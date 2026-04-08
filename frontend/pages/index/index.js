const app = getApp()
const {
  parseApiDateTime,
} = require('../../utils/util')

const API_BASE_URL = (app && app.globalData && app.globalData.apiBaseUrl) || 'http://127.0.0.1:18080'
const STUDENT_PROFILE_KEY = 'student_profile'
const STUDENT_SESSION_KEY = 'student_session'

Page({
  data: {
    assignments: [],
    loadingAssignments: false,
    showQuickCorrect: false,
    isProcessing: false,
    imageUrl: '',
    statusText: '',
    statusClass: '',
    submissionId: '',
    pollTimer: null,
    result: null,
    tempFilePath: '',
    userProfile: null,
    studentSession: null,
  },

  onLoad() {
    this.loadStudentIdentity()
    if (this.data.userProfile && !this.data.studentSession) {
      this.createStudentSession(this.data.userProfile)
    }
    this.loadAssignments()
  },

  onShow() {
    if (this.data.userProfile) {
      this.loadAssignments()
    }
  },

  onUnload() {
    this.clearPollTimer()
  },

  goTeacherPage() {
    wx.navigateTo({ url: '/pages/teacher/index' })
  },

  loadStudentIdentity() {
    const profile = (app && app.globalData && app.globalData.studentProfile) || wx.getStorageSync(STUDENT_PROFILE_KEY)
    const session = (app && app.globalData && app.globalData.studentSession) || wx.getStorageSync(STUDENT_SESSION_KEY)

    if (profile && profile.nickName) {
      if (app && app.globalData) app.globalData.studentProfile = profile
      this.setData({ userProfile: profile })
    }

    if (session && session.sessionToken) {
      if (app && app.globalData) app.globalData.studentSession = session
      this.setData({ studentSession: session })
    }
  },

  async createStudentSession(profile) {
    if (!profile || !profile.nickName) return null

    const existing = this.data.studentSession || wx.getStorageSync(STUDENT_SESSION_KEY)
    try {
      const session = await this.requestJson({
        url: `${API_BASE_URL}/api/v1/student/session`,
        method: 'POST',
        data: {
          display_name: profile.nickName,
          session_token: existing && existing.sessionToken ? existing.sessionToken : undefined,
        },
      })

      const normalized = {
        studentId: session.student_id,
        displayName: session.display_name,
        sessionToken: session.session_token,
      }

      wx.setStorageSync(STUDENT_SESSION_KEY, normalized)
      if (app && app.globalData) {
        app.globalData.studentSession = normalized
      }
      this.setData({ studentSession: normalized })
      return normalized
    } catch (err) {
      console.warn('Failed to create the student session', err)
      wx.showToast({ title: '学生会话初始化失败，请重试', icon: 'none' })
      return null
    }
  },

  async loginStudent() {
    try {
      const res = await new Promise((resolve, reject) => {
        wx.getUserProfile({
          desc: '用于识别你的作业批改记录',
          lang: 'zh_CN',
          success: resolve,
          fail: reject,
        })
      })

      const userInfo = res.userInfo || {}
      const profile = {
        nickName: userInfo.nickName || '微信同学',
        avatarUrl: userInfo.avatarUrl || '',
        gender: userInfo.gender || 0,
        province: userInfo.province || '',
        city: userInfo.city || '',
        loginAt: Date.now(),
      }

      const session = await this.createStudentSession(profile)
      if (!session) return

      wx.setStorageSync(STUDENT_PROFILE_KEY, profile)
      if (app && app.globalData) {
        app.globalData.studentProfile = profile
      }

      this.setData({
        userProfile: profile,
        studentSession: session,
      })
      wx.showToast({ title: '登录成功', icon: 'success' })
    } catch (err) {
      if (err && err.errMsg && err.errMsg.includes('cancel')) {
        return
      }
      console.warn('WeChat login failed', err)
      wx.showToast({ title: '登录失败，请重试', icon: 'none' })
    }
  },

  async loadAssignments() {
    this.setData({ loadingAssignments: true })

    try {
      const assignments = await this.requestJson({
        url: `${API_BASE_URL}/api/v1/assignments`,
      })

      const now = new Date()
      const processedAssignments = (assignments || []).map((item) => {
        const endTime = parseApiDateTime(item.submit_end_time)
        const startTime = parseApiDateTime(item.submit_start_time)

        let statusClass = 'draft'
        let statusText = '待开始'
        let isNearDeadline = false
        let countdown = ''

        if (item.publish_status === 'published') {
          if (endTime && now > endTime) {
            statusClass = 'ended'
            statusText = '已截止'
          } else if (startTime && now < startTime) {
            statusClass = 'draft'
            statusText = '待开始'
          } else {
            statusClass = 'active'
            statusText = '进行中'
            if (endTime) {
              const diff = endTime - now
              if (diff < 24 * 60 * 60 * 1000) {
                isNearDeadline = true
                statusClass = 'near-deadline'
                statusText = '即将截止'
                const hours = Math.max(0, Math.floor(diff / (60 * 60 * 1000)))
                const minutes = Math.max(0, Math.floor((diff % (60 * 60 * 1000)) / (60 * 1000)))
                countdown = `还剩 ${hours}小时${minutes}分`
              } else {
                const days = Math.floor(diff / (24 * 60 * 60 * 1000))
                countdown = `还剩 ${days} 天`
              }
            }
          }
        }

        const submitted = item.submitted_count || 0
        const total = item.total_students || 0
        const progressPercent = total > 0 ? Math.round((submitted / total) * 100) : 0

        return {
          ...item,
          statusClass,
          statusText,
          isNearDeadline,
          countdown,
          progress: `${submitted}/${total}`,
          progressPercent: Math.min(progressPercent, 100),
        }
      })

      const orderMap = { 'near-deadline': 0, active: 1, draft: 2, ended: 3 }
      processedAssignments.sort((a, b) => orderMap[a.statusClass] - orderMap[b.statusClass])

      this.setData({ assignments: processedAssignments })
    } catch (err) {
      console.warn('Failed to load assignments', err)
    } finally {
      this.setData({ loadingAssignments: false })
    }
  },

  goToAssignment(e) {
    const id = e.currentTarget.dataset.id
    if (!id) return
    wx.navigateTo({ url: `/pages/assignment/detail?id=${id}` })
  },

  showQuickCorrect() {
    this.setData({ showQuickCorrect: true })
  },

  hideQuickCorrect() {
    this.setData({ showQuickCorrect: false })
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
          reject(new Error(res.data?.detail || `请求失败 (${res.statusCode})`))
        },
        fail: () => reject(new Error('网络请求失败')),
      })
    })
  },

  logoutStudent() {
    wx.showModal({
      title: '退出登录',
      content: '退出后需要重新授权微信信息，是否继续？',
      confirmText: '退出',
      success: (res) => {
        if (!res.confirm) return

        if (app && app.globalData) {
          app.globalData.studentProfile = null
          app.globalData.studentSession = null
        }

        try {
          wx.removeStorageSync(STUDENT_PROFILE_KEY)
          wx.removeStorageSync(STUDENT_SESSION_KEY)
        } catch (err) {
          console.warn('Failed to clear the cached student identity', err)
        }

        this.setData({ userProfile: null, studentSession: null })
        wx.showToast({ title: '已退出', icon: 'none' })
      }
    })
  },

  getStudentName() {
    const session = this.data.studentSession
    if (session && session.displayName) return session.displayName
    const profile = this.data.userProfile
    return (profile && profile.nickName) ? profile.nickName : '未登录学生'
  },

  latexToHtml(text) {
    if (!text) return ''
    const fixed = text.replace(/\\\\/g, '\\')
    return fixed.replace(/\$([^$]+)\$/g, (match, latex) => {
      const encoded = encodeURIComponent(latex.trim())
      return `<img src="https://latex.codecogs.com/png.latex?\\dpi{150}${encoded}" style="display:inline-block;vertical-align:middle;height:1.4em;max-width:100%;" />`
    })
  },

  chooseImage() {
    if (this.data.isProcessing) return
    if (!this.data.userProfile) {
      wx.showToast({ title: '请先登录学生账号', icon: 'none' })
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
          result: null,
          statusText: '准备上传...',
          statusClass: 'processing',
        })
        this.quickCorrect(tempFilePath)
      },
      fail: (err) => {
        console.error('Failed to choose image', err)
        if (err.errMsg && !err.errMsg.includes('cancel')) {
          wx.showToast({ title: '选择图片失败', icon: 'none' })
        }
      }
    })
  },

  clearPollTimer() {
    if (this.data.pollTimer) {
      clearInterval(this.data.pollTimer)
      this.setData({ pollTimer: null })
    }
  },

  handleError(message) {
    this.clearPollTimer()
    wx.hideLoading()
    this.setData({
      isProcessing: false,
      statusText: `错误: ${message}`,
      statusClass: 'error',
    })
    wx.showToast({ title: message, icon: 'none', duration: 3000 })
  },

  quickCorrect(filePath) {
    this.setData({
      isProcessing: true,
      statusText: 'AI批改中（约需10-30秒）...',
      statusClass: 'processing',
    })

    let timeoutTimer = setTimeout(() => {
      this.handleError('请求超时，请检查网络或稍后重试')
    }, 60000)

    const clearTimeoutTimer = () => {
      if (timeoutTimer) {
        clearTimeout(timeoutTimer)
        timeoutTimer = null
      }
    }

    wx.uploadFile({
      url: `${API_BASE_URL}/api/v1/correct/upload`,
      filePath,
      name: 'file',
      formData: {
        student_name: this.getStudentName(),
      },
      header: { Accept: 'application/json' },
      success: (res) => {
        clearTimeoutTimer()
        wx.hideLoading()

        if (res.statusCode === 200) {
          try {
            const data = JSON.parse(res.data)
            const questions = (data.questions || []).map((q) => {
              let score = typeof q.score === 'string' ? parseFloat(q.score) : q.score
              let maxScore = typeof q.max_score === 'string' ? parseFloat(q.max_score) : q.max_score

              if (score === undefined || score === null || Number.isNaN(score)) {
                score = q.is_correct === true ? 10 : 0
              }
              if (maxScore === undefined || maxScore === null || Number.isNaN(maxScore)) {
                maxScore = 10
              }

              const percent = Math.round((score / maxScore) * 100)

              return {
                ...q,
                score,
                max_score: maxScore,
                content: this.latexToHtml(q.content),
                student_ans: this.latexToHtml(q.student_ans),
                analysis: this.latexToHtml(q.analysis),
                _barWidth: percent,
                _barClass: percent >= 60 ? 'good' : 'bad',
                _percent: percent,
                _statusClass: score >= maxScore ? 'correct-tag' : score > 0 ? 'partial-tag' : 'wrong-tag',
                _statusText: score >= maxScore ? '正确' : score > 0 ? '部分正确' : '错误',
                _showPartial: score > 0 && score < maxScore,
              }
            })

            this.setData({
              isProcessing: false,
              statusText: '批改完成',
              statusClass: 'completed',
              result: {
                student_name: this.getStudentName(),
                questions,
                total_score: questions.reduce((sum, item) => sum + (item.score || 0), 0),
                max_total_score: questions.reduce((sum, item) => sum + (item.max_score || 10), 0),
                ocrText: data._ocr_extracted || '',
              },
            })
            wx.showToast({ title: '批改完成', icon: 'success' })
          } catch (err) {
            console.error('Failed to parse the correction response', err, res.data)
            this.handleError('解析结果失败')
          }
        } else {
          let message = `批改失败 (${res.statusCode})`
          try {
            const err = JSON.parse(res.data)
            message = err.detail?.message || err.detail || message
          } catch (parseErr) {}
          this.handleError(message)
        }
      },
      fail: (err) => {
        clearTimeoutTimer()
        console.error('Upload request failed', err)
        this.handleError('网络连接失败，请检查后端服务')
      }
    })

    wx.showLoading({ title: 'AI批改中...', mask: true })
  },
})
