const app = getApp()
const {
  formatDisplayDateTime,
  parseApiDateTime,
} = require('../../utils/util')

const API_BASE_URL = (app && app.globalData && app.globalData.apiBaseUrl) || 'http://127.0.0.1:18080'
const STUDENT_SESSION_KEY = 'student_session'

Page({
  data: {
    assignmentId: '',
    assignment: null,
    loading: true,
    error: '',
    hasSubmitted: false,
    submission: null,
    isUploading: false,
    imageUrl: '',
    tempFilePath: '',
  },

  onLoad(options) {
    const { id } = options
    if (!id) {
      wx.showToast({ title: '作业ID缺失', icon: 'none' })
      wx.navigateBack()
      return
    }

    this.setData({ assignmentId: id })
    this.loadAssignmentDetail()
  },

  onShow() {
    if (this.data.assignmentId) {
      this.loadSubmissionStatus()
    }
  },

  onPullDownRefresh() {
    Promise.all([
      this.loadAssignmentDetail(),
      this.loadSubmissionStatus(),
    ]).finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  getStudentSession() {
    return (app && app.globalData && app.globalData.studentSession) || wx.getStorageSync(STUDENT_SESSION_KEY)
  },

  getStudentName() {
    const session = this.getStudentSession()
    return session && session.displayName ? session.displayName : '未知学生'
  },

  async loadAssignmentDetail() {
    this.setData({ loading: true, error: '' })

    try {
      const assignment = await this.requestJson({
        url: `${API_BASE_URL}/api/v1/assignments/${this.data.assignmentId}`,
      })

      const now = new Date()
      const endTime = parseApiDateTime(assignment.submit_end_time)
      const startTime = parseApiDateTime(assignment.submit_start_time)

      let statusText = '进行中'
      let statusClass = 'active'
      let canSubmit = true
      let timeStatus = ''

      if (assignment.publish_status !== 'published') {
        statusText = '未发布'
        statusClass = 'draft'
        canSubmit = false
      } else if (endTime && now > endTime) {
        statusText = '已截止'
        statusClass = 'ended'
        canSubmit = assignment.allow_late
        timeStatus = '已截止'
      } else if (startTime && now < startTime) {
        statusText = '未开始'
        statusClass = 'pending'
        canSubmit = false
        timeStatus = `开始时间 ${formatDisplayDateTime(assignment.submit_start_time)}`
      } else if (endTime) {
        const diff = endTime - now
        const days = Math.floor(diff / (24 * 60 * 60 * 1000))
        const hours = Math.floor((diff % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000))

        if (days > 0) {
          timeStatus = `还剩 ${days} 天${hours} 小时`
        } else {
          timeStatus = `还剩 ${Math.max(0, hours)} 小时`
          statusClass = 'near'
        }
      }

      this.setData({
        assignment: {
          ...assignment,
          statusText,
          statusClass,
          canSubmit,
          timeStatus,
          formattedStartTime: formatDisplayDateTime(assignment.submit_start_time),
          formattedEndTime: formatDisplayDateTime(assignment.submit_end_time),
          formattedAppealTime: formatDisplayDateTime(assignment.appeal_end_time),
        },
        loading: false,
      })

      this.loadSubmissionStatus()
    } catch (err) {
      this.setData({
        loading: false,
        error: err.message || '加载作业详情失败',
      })
    }
  },

  async loadSubmissionStatus() {
    const session = this.getStudentSession()
    if (!session || !session.sessionToken) {
      this.setData({ hasSubmitted: false, submission: null })
      return
    }

    try {
      const submission = await this.requestJson({
        url: `${API_BASE_URL}/api/v1/assignments/${this.data.assignmentId}/submissions/me`,
        header: {
          'X-Student-Token': session.sessionToken,
        },
      })

      this.setData({
        hasSubmitted: true,
        submission,
      })
    } catch (err) {
      this.setData({ hasSubmitted: false, submission: null })
    }
  },

  chooseAndSubmit() {
    if (!this.data.assignment?.canSubmit) {
      wx.showToast({ title: '当前不可提交', icon: 'none' })
      return
    }

    if (!this.getStudentSession()?.sessionToken) {
      wx.showToast({ title: '请先返回首页完成学生登录', icon: 'none' })
      return
    }

    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      camera: 'back',
      success: (res) => {
        const tempFilePath = res.tempFiles[0].tempFilePath
        this.setData({
          imageUrl: tempFilePath,
          tempFilePath,
        })
      },
    })
  },

  submitAssignment() {
    const session = this.getStudentSession()
    const filePath = this.data.tempFilePath

    if (!filePath) {
      wx.showToast({ title: '请先选择图片', icon: 'none' })
      return
    }

    if (!session || !session.sessionToken) {
      wx.showToast({ title: '请先返回首页完成学生登录', icon: 'none' })
      return
    }

    this.setData({ isUploading: true })

    wx.uploadFile({
      url: `${API_BASE_URL}/api/v1/assignments/${this.data.assignmentId}/submit`,
      filePath,
      name: 'file',
      header: {
        'X-Student-Token': session.sessionToken,
      },
      success: (res) => {
        if (res.statusCode === 202) {
          const data = JSON.parse(res.data)
          wx.showToast({ title: '提交成功', icon: 'success' })

          this.setData({
            hasSubmitted: true,
            submission: {
              submission_id: data.submission_id,
              status: 'processing',
            },
          })

          this.pollSubmissionStatus(data.submission_id)
          return
        }

        let message = '提交失败'
        try {
          const err = JSON.parse(res.data)
          message = err.detail || message
        } catch (parseErr) {}
        wx.showToast({ title: message, icon: 'none' })
      },
      fail: () => {
        wx.showToast({ title: '网络错误', icon: 'none' })
      },
      complete: () => {
        this.setData({ isUploading: false })
      },
    })
  },

  pollSubmissionStatus(submissionId) {
    const session = this.getStudentSession()
    if (!session || !session.sessionToken) return

    const poll = () => {
      this.requestJson({
        url: `${API_BASE_URL}/api/v1/assignments/${this.data.assignmentId}/submissions/${submissionId}`,
        header: {
          'X-Student-Token': session.sessionToken,
        },
      }).then((data) => {
        this.setData({ submission: data })

        if (data.status === 'processing') {
          setTimeout(poll, 2000)
        } else if (data.status === 'completed') {
          wx.showToast({ title: '批改完成', icon: 'success' })
        } else if (data.status === 'failed') {
          wx.showToast({ title: '批改失败', icon: 'none' })
        }
      }).catch(() => {})
    }

    poll()
  },

  viewResult() {
    const { submission } = this.data
    if (!submission || submission.status !== 'completed') {
      wx.showToast({ title: '批改尚未完成', icon: 'none' })
      return
    }

    const questions = submission.questions || []
    const resultData = {
      assignment_title: this.data.assignment?.title,
      total_score: submission.total_score,
      max_total_score: submission.max_total_score,
      questions: questions.map((q) => ({
        ...q,
        _statusClass: q.score >= q.max_score ? 'correct' : q.score > 0 ? 'partial' : 'wrong',
        _statusText: q.score >= q.max_score ? '正确' : q.score > 0 ? '部分正确' : '错误',
      })),
    }

    app.globalData = app.globalData || {}
    app.globalData.lastResult = resultData

    wx.navigateTo({
      url: '/pages/assignment/result'
    })
  },

  resubmit() {
    if (!this.data.assignment?.allow_resubmit) {
      wx.showToast({ title: '该作业不允许重新提交', icon: 'none' })
      return
    }

    wx.showModal({
      title: '重新提交',
      content: '重新提交将覆盖之前的提交记录，是否继续？',
      confirmText: '继续',
      success: (res) => {
        if (res.confirm) {
          this.chooseAndSubmit()
        }
      },
    })
  },

  previewImage() {
    if (this.data.imageUrl) {
      wx.previewImage({
        urls: [this.data.imageUrl],
      })
    }
  },

  goBack() {
    wx.navigateBack()
  },

  requestJson({ url, method = 'GET', data = null, header = {} }) {
    return new Promise((resolve, reject) => {
      wx.request({
        url,
        method,
        data,
        header: {
          'Content-Type': 'application/json',
          ...header,
        },
        success: (res) => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(res.data)
            return
          }

          const detail = res.data?.detail
          const message = typeof detail === 'string'
            ? detail
            : (detail && detail.message) || `请求失败 (${res.statusCode})`
          reject(new Error(message))
        },
        fail: () => reject(new Error('网络请求失败')),
      })
    })
  },
})
