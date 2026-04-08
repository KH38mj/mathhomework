const app = getApp()
const {
  formatApiDateTime,
  formatDisplayDateTime,
  parseApiDateTime,
} = require('../../utils/util')

const API_BASE_URL = (app && app.globalData && app.globalData.apiBaseUrl) || 'http://127.0.0.1:18080'

Page({
  data: {
    activeTab: 'course',
    assignmentSubTab: 'list',
    assignments: [],
    loadingAssignments: false,
    loadingCourses: false,
    courses: [],
    selectedCourseIndex: -1,
    selectedCourseId: '',
    selectedCourseName: '',
    rosterStudents: [],
    courseIdInput: '',
    courseNameInput: '',
    studentIdInput: '',
    studentNameInput: '',
    classNameInput: '',
    importFilePath: '',
    importFileName: '',
    assignmentMode: null,
    assignmentTitle: '',
    questionContent: '',
    maxScoreInput: '10',
    teacherAnswer: '',
    createdAssignment: null,
    solveImagePath: '',
    solveImagePreview: '',
    solveSpecifications: '',
    solveLoading: false,
    extractedQuestion: null,
    assignmentStartTime: '',
    assignmentStartTimeValue: '',
    assignmentEndTime: '',
    assignmentEndTimeValue: '',
    assignmentAppealTime: '',
    assignmentAppealTimeValue: '',
    dateTimeArray: null,
    dateTimeStart: [0, 0, 0, 0, 0],
    dateTimeEnd: [0, 0, 0, 0, 0],
    dateTimeAppeal: [0, 0, 0, 0, 0],
    allowResubmit: true,
    allowLate: true,
    lateRules: ['逾期按100%计分', '逾期按80%计分', '逾期按60%计分', '逾期按0%计分（拒收）'],
    lateRuleIndex: 0,
    lateRuleValues: ['100%', '80%', '60%', '0%'],
  },

  onLoad() {
    this.initDateTimePicker()
    this.loadCourses()
    this.loadAssignments()
  },

  initDateTimePicker() {
    const years = []
    const months = []
    const days = []
    const hours = []
    const minutes = []
    const currentYear = new Date().getFullYear()

    for (let year = currentYear - 1; year <= currentYear + 5; year += 1) {
      years.push(`${year}`)
    }
    for (let month = 1; month <= 12; month += 1) {
      months.push(`${month}`.padStart(2, '0'))
    }
    for (let day = 1; day <= 31; day += 1) {
      days.push(`${day}`.padStart(2, '0'))
    }
    for (let hour = 0; hour < 24; hour += 1) {
      hours.push(`${hour}`.padStart(2, '0'))
    }
    for (let minute = 0; minute < 60; minute += 5) {
      minutes.push(`${minute}`.padStart(2, '0'))
    }

    const now = new Date()
    const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000)
    const defaultValue = [
      years.indexOf(`${currentYear}`),
      now.getMonth(),
      now.getDate() - 1,
      now.getHours(),
      Math.floor(now.getMinutes() / 5),
    ]
    const endValue = [
      years.indexOf(`${tomorrow.getFullYear()}`),
      tomorrow.getMonth(),
      tomorrow.getDate() - 1,
      tomorrow.getHours(),
      Math.floor(tomorrow.getMinutes() / 5),
    ]

    this.setData({
      dateTimeArray: [years, months, days, hours, minutes],
      dateTimeStart: defaultValue,
      dateTimeEnd: endValue,
      dateTimeAppeal: defaultValue,
      assignmentStartTime: formatDisplayDateTime(now),
      assignmentStartTimeValue: formatApiDateTime(now),
      assignmentEndTime: formatDisplayDateTime(tomorrow),
      assignmentEndTimeValue: formatApiDateTime(tomorrow),
      assignmentAppealTime: '',
      assignmentAppealTimeValue: '',
    })
  },

  onPullDownRefresh() {
    Promise.all([this.loadCourses(), this.loadAssignments()]).finally(() => wx.stopPullDownRefresh())
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })
    if (tab === 'assignment') {
      this.loadAssignments()
    }
  },

  switchAssignmentSubTab(e) {
    const subtab = e.currentTarget.dataset.subtab
    this.setData({ assignmentSubTab: subtab })
    if (subtab === 'list') {
      this.loadAssignments()
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
        let statusText = '草稿'
        let isNearDeadline = false

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
            if (endTime && (endTime - now) < 24 * 60 * 60 * 1000) {
              statusClass = 'near-deadline'
              statusText = '即将截止'
              isNearDeadline = true
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
          progressPercent: Math.min(progressPercent, 100),
          progress: `${submitted}/${total}`,
          submit_start_time_raw: item.submit_start_time,
          submit_end_time_raw: item.submit_end_time,
          appeal_end_time_raw: item.appeal_end_time,
          submit_start_time: formatDisplayDateTime(item.submit_start_time),
          submit_end_time: formatDisplayDateTime(item.submit_end_time),
          appeal_end_time: formatDisplayDateTime(item.appeal_end_time),
        }
      })

      this.setData({ assignments: processedAssignments })
    } catch (err) {
      wx.showToast({ title: err.message || '加载作业列表失败', icon: 'none' })
    } finally {
      this.setData({ loadingAssignments: false })
    }
  },

  viewAssignmentDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '作业详情',
      content: `作业ID: ${id}\n\n更多详情页还没接上，先别嫌它简陋。`,
      showCancel: false,
    })
  },

  showExtendDeadline(e) {
    const id = e.currentTarget.dataset.id
    const currentEndTime = e.currentTarget.dataset.endtime || '未设置'

    wx.showModal({
      title: '延长截止时间',
      content: `当前截止时间：${currentEndTime}\n\n选择一个延长方案吧。`,
      confirmText: '继续',
      success: (res) => {
        if (res.confirm) {
          this.showDateTimePickerForExtend(id)
        }
      }
    })
  },

  showDateTimePickerForExtend(assignmentId) {
    wx.showActionSheet({
      itemList: ['延长1天', '延长3天', '延长7天'],
      success: (res) => {
        const days = [1, 3, 7][res.tapIndex]
        if (days) {
          this.extendDeadline(assignmentId, days)
        }
      }
    })
  },

  async extendDeadline(assignmentId, days) {
    wx.showLoading({ title: '更新中...', mask: true })

    try {
      const assignment = this.data.assignments.find((item) => item.id === assignmentId)
      if (!assignment) {
        throw new Error('作业不存在')
      }

      const currentEndTime = parseApiDateTime(assignment.submit_end_time_raw) || new Date()
      const newEndTime = new Date(currentEndTime.getTime() + days * 24 * 60 * 60 * 1000)

      await this.requestJson({
        url: `${API_BASE_URL}/api/v1/assignments/${assignmentId}/extend`,
        method: 'POST',
        data: {
          submit_end_time: formatApiDateTime(newEndTime),
        }
      })

      wx.showToast({ title: `已延长${days}天`, icon: 'success' })
      this.loadAssignments()
    } catch (err) {
      wx.showToast({ title: err.message || '延长失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  },

  goToAdmin() {
    wx.navigateTo({ url: '/pages/admin/index' })
  },

  onFieldInput(e) {
    const key = e.currentTarget.dataset.key
    if (!key) return
    this.setData({ [key]: e.detail.value })
  },

  async loadCourses() {
    this.setData({ loadingCourses: true })

    try {
      const courses = await this.requestJson({
        url: `${API_BASE_URL}/api/v1/courses`,
      })

      const list = Array.isArray(courses) ? courses : []
      let selectedCourseIndex = this.data.selectedCourseIndex

      if (!list.length) {
        this.setData({
          courses: [],
          selectedCourseIndex: -1,
          selectedCourseId: '',
          selectedCourseName: '',
          rosterStudents: [],
        })
        return
      }

      const oldId = this.data.selectedCourseId
      if (oldId) {
        const idx = list.findIndex((course) => course.course_id === oldId)
        selectedCourseIndex = idx >= 0 ? idx : 0
      } else {
        selectedCourseIndex = 0
      }

      const selected = list[selectedCourseIndex]
      this.setData({
        courses: list,
        selectedCourseIndex,
        selectedCourseId: selected.course_id,
        selectedCourseName: selected.course_name,
        rosterStudents: selected.students || [],
      })
    } catch (err) {
      wx.showToast({ title: err.message || '加载课程失败', icon: 'none' })
    } finally {
      this.setData({ loadingCourses: false })
    }
  },

  onCoursePickerChange(e) {
    const index = Number(e.detail.value)
    const selected = this.data.courses[index]
    if (!selected) return

    this.setData({
      selectedCourseIndex: index,
      selectedCourseId: selected.course_id,
      selectedCourseName: selected.course_name,
      rosterStudents: selected.students || [],
    })
  },

  async createCourse() {
    const courseId = (this.data.courseIdInput || '').trim()
    const courseName = (this.data.courseNameInput || '').trim()
    if (!courseId || !courseName) {
      wx.showToast({ title: '请填写课程编号和课程名称', icon: 'none' })
      return
    }

    wx.showLoading({ title: '创建中...', mask: true })
    try {
      await this.requestJson({
        url: `${API_BASE_URL}/api/v1/courses`,
        method: 'POST',
        data: {
          course_id: courseId,
          course_name: courseName,
        }
      })

      this.setData({
        courseIdInput: '',
        courseNameInput: '',
      })

      await this.loadCourses()
      wx.showToast({ title: '课程创建成功', icon: 'success' })
    } catch (err) {
      wx.showToast({ title: err.message || '创建课程失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  },

  async addStudent() {
    const courseId = this.data.selectedCourseId
    if (!courseId) {
      wx.showToast({ title: '请先创建或选择课程', icon: 'none' })
      return
    }

    const studentId = (this.data.studentIdInput || '').trim()
    const name = (this.data.studentNameInput || '').trim()
    const className = (this.data.classNameInput || '').trim()

    if (!studentId || !name) {
      wx.showToast({ title: '请填写学号和姓名', icon: 'none' })
      return
    }

    wx.showLoading({ title: '添加中...', mask: true })
    try {
      const roster = await this.requestJson({
        url: `${API_BASE_URL}/api/v1/courses/${courseId}/students`,
        method: 'POST',
        data: {
          student_id: studentId,
          name,
          class_name: className,
        }
      })

      this.setData({
        rosterStudents: roster.students || [],
        studentIdInput: '',
        studentNameInput: '',
        classNameInput: '',
      })

      await this.loadCourses()
      wx.showToast({ title: '学生已添加', icon: 'success' })
    } catch (err) {
      wx.showToast({ title: err.message || '添加失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  },

  async removeStudent(e) {
    const studentId = e.currentTarget.dataset.sid
    const courseId = this.data.selectedCourseId
    if (!studentId || !courseId) return

    wx.showLoading({ title: '移除中...', mask: true })
    try {
      const roster = await this.requestJson({
        url: `${API_BASE_URL}/api/v1/courses/${courseId}/students/${studentId}`,
        method: 'DELETE',
      })

      this.setData({ rosterStudents: roster.students || [] })
      await this.loadCourses()
      wx.showToast({ title: '已移除', icon: 'success' })
    } catch (err) {
      wx.showToast({ title: err.message || '移除失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  },

  chooseRosterFile() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['csv', 'xlsx'],
      success: (res) => {
        const file = res.tempFiles && res.tempFiles[0]
        if (!file) return
        this.setData({
          importFilePath: file.path,
          importFileName: file.name || '未命名文件',
        })
      },
      fail: (err) => {
        if (err && err.errMsg && err.errMsg.includes('cancel')) return
        wx.showToast({ title: '选择文件失败', icon: 'none' })
      }
    })
  },

  importStudents() {
    const courseId = this.data.selectedCourseId
    const filePath = this.data.importFilePath

    if (!courseId) {
      wx.showToast({ title: '请先创建或选择课程', icon: 'none' })
      return
    }

    if (!filePath) {
      wx.showToast({ title: '请先选择 CSV/XLSX 文件', icon: 'none' })
      return
    }

    wx.showLoading({ title: '导入中...', mask: true })

    wx.uploadFile({
      url: `${API_BASE_URL}/api/v1/courses/${courseId}/students/import`,
      filePath,
      name: 'file',
      success: async (res) => {
        wx.hideLoading()
        if (res.statusCode < 200 || res.statusCode >= 300) {
          let message = `导入失败 (${res.statusCode})`
          try {
            const data = JSON.parse(res.data)
            message = typeof data.detail === 'string' ? data.detail : message
          } catch (err) {}
          wx.showToast({ title: message, icon: 'none' })
          return
        }

        try {
          const roster = JSON.parse(res.data)
          this.setData({
            rosterStudents: roster.students || [],
            importFilePath: '',
            importFileName: '',
          })
          await this.loadCourses()
          wx.showToast({ title: '导入成功', icon: 'success' })
        } catch (err) {
          wx.showToast({ title: '导入结果解析失败', icon: 'none' })
        }
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: '导入请求失败', icon: 'none' })
      }
    })
  },

  selectAssignmentMode(e) {
    const mode = e.currentTarget.dataset.mode
    this.setData({
      assignmentMode: mode,
      createdAssignment: null,
    })
  },

  resetAssignmentMode() {
    this.initDateTimePicker()
    this.setData({
      assignmentMode: null,
      assignmentTitle: '',
      questionContent: '',
      teacherAnswer: '',
      maxScoreInput: '10',
      solveImagePath: '',
      solveImagePreview: '',
      solveSpecifications: '',
      extractedQuestion: null,
      createdAssignment: null,
    })
  },

  createAnotherAssignment() {
    this.setData({
      createdAssignment: null,
      assignmentTitle: '',
      questionContent: '',
      teacherAnswer: '',
      maxScoreInput: '10',
      solveImagePath: '',
      solveImagePreview: '',
      solveSpecifications: '',
      extractedQuestion: null,
      assignmentSubTab: 'create',
    })
  },

  onStartTimeChange(e) {
    const value = e.detail.value
      const date = this.buildDateFromPicker(value)
      this.setData({
        dateTimeStart: value,
        assignmentStartTime: formatDisplayDateTime(date),
        assignmentStartTimeValue: formatApiDateTime(date),
      })
  },

  onEndTimeChange(e) {
    const value = e.detail.value
      const date = this.buildDateFromPicker(value)
      this.setData({
        dateTimeEnd: value,
        assignmentEndTime: formatDisplayDateTime(date),
        assignmentEndTimeValue: formatApiDateTime(date),
      })
  },

  onAppealTimeChange(e) {
    const value = e.detail.value
      const date = this.buildDateFromPicker(value)
      this.setData({
        dateTimeAppeal: value,
        assignmentAppealTime: formatDisplayDateTime(date),
        assignmentAppealTimeValue: formatApiDateTime(date),
      })
  },

  onStartTimeColumnChange() {},
  onEndTimeColumnChange() {},
  onAppealTimeColumnChange() {},

  buildDateFromPicker(arr) {
    if (!this.data.dateTimeArray) return new Date()
    const [years, months, days, hours, minutes] = this.data.dateTimeArray
    const year = Number(years[arr[0]])
    const month = Number(months[arr[1]]) - 1
    const day = Number(days[arr[2]])
    const hour = Number(hours[arr[3]])
    const minute = Number(minutes[arr[4]])
    return new Date(year, month, day, hour, minute, 0)
  },

  onAllowResubmitChange(e) {
    this.setData({ allowResubmit: e.detail.value })
  },

  onAllowLateChange(e) {
    this.setData({ allowLate: e.detail.value })
  },

  onLateRuleChange(e) {
    this.setData({ lateRuleIndex: e.detail.value })
  },

  async createAssignmentManual() {
    const title = (this.data.assignmentTitle || '').trim()
    const questionContent = (this.data.questionContent || '').trim()
    const teacherAnswer = (this.data.teacherAnswer || '').trim()
    const maxScore = Number(this.data.maxScoreInput)

    if (!title || !questionContent || !teacherAnswer) {
      wx.showToast({ title: '请完整填写作业信息', icon: 'none' })
      return
    }
    if (!Number.isFinite(maxScore) || maxScore <= 0) {
      wx.showToast({ title: '满分必须是大于0的数字', icon: 'none' })
      return
    }

    wx.showLoading({ title: '创建中...', mask: true })
    try {
      const assignment = await this.requestJson({
        url: `${API_BASE_URL}/api/v1/assignments`,
        method: 'POST',
        data: {
          title,
          questions: [
            {
              type: 'text',
              content: questionContent,
              max_score: maxScore,
            }
          ],
          submit_start_time: this.data.assignmentStartTimeValue,
          submit_end_time: this.data.assignmentEndTimeValue,
          appeal_end_time: this.data.assignmentAppealTimeValue || null,
          allow_resubmit: this.data.allowResubmit,
          allow_late: this.data.allowLate,
          late_score_rule: this.data.lateRuleValues[this.data.lateRuleIndex],
          course_id: this.data.selectedCourseId || null,
        }
      })

      await this.requestJson({
        url: `${API_BASE_URL}/api/v1/assignments/${assignment.id}/answers/teacher-submit`,
        method: 'POST',
        data: {
          answers: [
            {
              question_index: 0,
              answer: teacherAnswer,
            }
          ]
        }
      })

      this.setData({
        createdAssignment: {
          id: assignment.id,
          title: assignment.title,
        },
        assignmentSubTab: 'list',
      })

      wx.showToast({ title: '作业创建成功', icon: 'success' })
      this.loadAssignments()
    } catch (err) {
      wx.showToast({ title: err.message || '创建作业失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  },

  chooseSolveImage() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const file = res.tempFiles[0]
        if (!file) return
        this.setData({
          solveImagePath: file.tempFilePath,
          solveImagePreview: file.tempFilePath,
          extractedQuestion: null,
        })
      },
      fail: (err) => {
        if (err && err.errMsg && err.errMsg.includes('cancel')) return
        wx.showToast({ title: '选择图片失败', icon: 'none' })
      }
    })
  },

  onSolveSpecInput(e) {
    this.setData({ solveSpecifications: e.detail.value })
  },

  solveAndExtractQuestion() {
    const { solveImagePath, solveSpecifications } = this.data

    if (!solveImagePath) {
      wx.showToast({ title: '请先选择题目图片', icon: 'none' })
      return
    }
    if (!solveSpecifications.trim()) {
      wx.showToast({ title: '请输入题目指定', icon: 'none' })
      return
    }

    this.setData({ solveLoading: true })

    wx.uploadFile({
      url: `${API_BASE_URL}/api/v1/solve/upload`,
      filePath: solveImagePath,
      name: 'file',
      formData: {
        specifications: solveSpecifications.trim(),
      },
      success: (res) => {
        if (res.statusCode < 200 || res.statusCode >= 300) {
          let message = `识别失败 (${res.statusCode})`
          try {
            const data = JSON.parse(res.data)
            const detail = data && data.detail
            message = typeof detail === 'string' ? detail : (detail && detail.message) || message
          } catch (err) {}
          wx.showToast({ title: message, icon: 'none', duration: 3000 })
          this.setData({ solveLoading: false })
          return
        }

        try {
          const result = JSON.parse(res.data)
          const questions = result.specified_questions || []
          if (!questions.length || !questions[0].found) {
            wx.showToast({ title: '没找到指定题目，请检查格式', icon: 'none' })
            this.setData({ solveLoading: false })
            return
          }

          const question = questions[0]
          this.setData({
            extractedQuestion: {
              specification: question.specification,
              content: question.content || '',
              full_solution: question.full_solution || '',
              question_type: question.question_type || '',
              difficulty: question.difficulty || '',
              knowledge_points: question.knowledge_points || [],
              knowledge_points_str: (question.knowledge_points || []).join('、'),
              max_score: 10,
            },
            solveLoading: false,
          })

          wx.showToast({ title: '识别成功，请核对后创建', icon: 'success' })
        } catch (err) {
          wx.showToast({ title: '解析结果失败', icon: 'none' })
          this.setData({ solveLoading: false })
        }
      },
      fail: () => {
        wx.showToast({ title: '请求失败', icon: 'none' })
        this.setData({ solveLoading: false })
      }
    })
  },

  onExtractedFieldInput(e) {
    const key = e.currentTarget.dataset.key
    if (!key || !this.data.extractedQuestion) return

    const mapping = {
      extractedContent: 'content',
      extractedAnswer: 'full_solution',
      extractedMaxScore: 'max_score',
    }

    const targetKey = mapping[key] || key
    this.setData({
      [`extractedQuestion.${targetKey}`]: e.detail.value,
    })
  },

  async createAssignmentFromPhoto() {
    const title = (this.data.assignmentTitle || '').trim()
    const extractedQuestion = this.data.extractedQuestion

    if (!title) {
      wx.showToast({ title: '请填写作业标题', icon: 'none' })
      return
    }
    if (!extractedQuestion || !extractedQuestion.content) {
      wx.showToast({ title: '题目内容不能为空', icon: 'none' })
      return
    }

    const maxScore = Number(extractedQuestion.max_score)
    if (!Number.isFinite(maxScore) || maxScore <= 0) {
      wx.showToast({ title: '满分必须是大于0的数字', icon: 'none' })
      return
    }

    wx.showLoading({ title: '创建中...', mask: true })
    try {
      const assignment = await this.requestJson({
        url: `${API_BASE_URL}/api/v1/assignments`,
        method: 'POST',
        data: {
          title,
          questions: [
            {
              type: 'text',
              content: extractedQuestion.content,
              max_score: maxScore,
            }
          ],
          submit_start_time: this.data.assignmentStartTimeValue,
          submit_end_time: this.data.assignmentEndTimeValue,
          appeal_end_time: this.data.assignmentAppealTimeValue || null,
          allow_resubmit: this.data.allowResubmit,
          allow_late: this.data.allowLate,
          late_score_rule: this.data.lateRuleValues[this.data.lateRuleIndex],
          course_id: this.data.selectedCourseId || null,
        }
      })

      await this.requestJson({
        url: `${API_BASE_URL}/api/v1/assignments/${assignment.id}/answers/teacher-submit`,
        method: 'POST',
        data: {
          answers: [
            {
              question_index: 0,
              answer: extractedQuestion.full_solution || '暂无答案',
            }
          ]
        }
      })

      this.setData({
        createdAssignment: {
          id: assignment.id,
          title: assignment.title,
        },
        assignmentSubTab: 'list',
      })

      wx.showToast({ title: '作业创建成功', icon: 'success' })
      this.loadAssignments()
    } catch (err) {
      wx.showToast({ title: err.message || '创建作业失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  },

  copyAssignmentId() {
    const assignment = this.data.createdAssignment
    if (!assignment || !assignment.id) return

    wx.setClipboardData({
      data: assignment.id,
      success: () => wx.showToast({ title: '作业ID已复制', icon: 'success' }),
    })
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

          const detail = res.data && res.data.detail
          const message = typeof detail === 'string'
            ? detail
            : (detail && detail.message) || `请求失败 (${res.statusCode})`
          reject(new Error(message))
        },
        fail: () => reject(new Error('网络请求失败，请检查后端服务')),
      })
    })
  },
})
