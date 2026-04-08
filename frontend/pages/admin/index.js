const app = getApp()

const API_BASE_URL = (app && app.globalData && app.globalData.apiBaseUrl) || 'http://127.0.0.1:18080'
const ADMIN_TOKEN_KEY = 'admin_token'

Page({
  data: {
    isLoggedIn: false,
    password: '',
    currentConfig: {
      AI_VISION_API_BASE_URL: '',
      AI_VISION_MODEL_NAME: '',
      AI_TEXT_API_BASE_URL: '',
      AI_TEXT_MODEL_NAME: '',
      SOLVE_API_BASE_URL: '',
      SOLVE_MODEL_NAME: '',
    },
    aiStatus: {
      vision: false,
      text: false,
      solve: false,
    },
    testing: false,
    configForm: {
      visionBaseUrl: '',
      visionKey: '',
      visionModel: '',
      textBaseUrl: '',
      textKey: '',
      textModel: '',
      solveBaseUrl: '',
      solveKey: '',
      solveModel: '',
    },
    modelLists: {
      vision: [],
      visionSelectedIndex: -1,
      visionSelectedDesc: '',
      text: [],
      textSelectedIndex: -1,
      textSelectedDesc: '',
      solve: [],
      solveSelectedIndex: -1,
      solveSelectedDesc: '',
    },
    fetchingModels: {
      vision: false,
      text: false,
      solve: false,
    },
    saving: false,
    saveResult: {
      show: false,
      success: false,
      message: '',
    },
  },

  onLoad() {
    const adminToken = wx.getStorageSync(ADMIN_TOKEN_KEY)
    if (adminToken) {
      this.setData({ isLoggedIn: true })
      this.loadConfig().catch(() => this.logout())
    }
  },

  onShow() {
    if (this.data.isLoggedIn) {
      this.loadConfig().catch(() => this.logout())
    }
  },

  getAdminToken() {
    return wx.getStorageSync(ADMIN_TOKEN_KEY)
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  async login() {
    const password = this.data.password.trim()
    if (!password) {
      wx.showToast({ title: '请输入密码', icon: 'none' })
      return
    }

    wx.showLoading({ title: '验证中...' })

    try {
      const res = await this.request({
        url: `${API_BASE_URL}/api/v1/admin/login`,
        method: 'POST',
        data: { password },
      })

      if (!res.success || !res.token) {
        wx.showToast({ title: '登录失败', icon: 'none' })
        return
      }

      wx.setStorageSync(ADMIN_TOKEN_KEY, res.token)
      this.setData({
        isLoggedIn: true,
        password: '',
      })
      await this.loadConfig()
      wx.showToast({ title: '登录成功', icon: 'success' })
    } catch (err) {
      wx.showToast({ title: err.message || '登录失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  },

  logout() {
    wx.removeStorageSync(ADMIN_TOKEN_KEY)
    this.setData({
      isLoggedIn: false,
      password: '',
    })
  },

  async loadConfig() {
    const adminToken = this.getAdminToken()
    if (!adminToken) return

    const config = await this.request({
      url: `${API_BASE_URL}/api/v1/admin/config`,
      header: { 'X-Admin-Token': adminToken },
    })

    this.setData({
      currentConfig: config,
      aiStatus: {
        vision: !!config.AI_VISION_MODEL_NAME,
        text: !!config.AI_TEXT_MODEL_NAME,
        solve: !!config.SOLVE_MODEL_NAME,
      },
      configForm: {
        visionBaseUrl: config.AI_VISION_API_BASE_URL || '',
        visionKey: '',
        visionModel: config.AI_VISION_MODEL_NAME || '',
        textBaseUrl: config.AI_TEXT_API_BASE_URL || '',
        textKey: '',
        textModel: config.AI_TEXT_MODEL_NAME || '',
        solveBaseUrl: config.SOLVE_API_BASE_URL || '',
        solveKey: '',
        solveModel: config.SOLVE_MODEL_NAME || '',
      },
    })
  },

  onConfigInput(e) {
    const key = e.currentTarget.dataset.key
    if (!key) return
    this.setData({ [`configForm.${key}`]: e.detail.value })
  },

  resetForm() {
    this.loadConfig()
      .then(() => wx.showToast({ title: '已重置', icon: 'none' }))
      .catch(() => this.logout())
  },

  async saveConfig() {
    const adminToken = this.getAdminToken()
    if (!adminToken) {
      this.logout()
      return
    }

    const { configForm } = this.data
    const updates = {}

    if (configForm.visionBaseUrl.trim()) updates.AI_VISION_API_BASE_URL = configForm.visionBaseUrl.trim()
    if (configForm.visionKey.trim()) updates.AI_VISION_API_KEY = configForm.visionKey.trim()
    if (configForm.visionModel.trim()) updates.AI_VISION_MODEL_NAME = configForm.visionModel.trim()
    if (configForm.textBaseUrl.trim()) updates.AI_TEXT_API_BASE_URL = configForm.textBaseUrl.trim()
    if (configForm.textKey.trim()) updates.AI_TEXT_API_KEY = configForm.textKey.trim()
    if (configForm.textModel.trim()) updates.AI_TEXT_MODEL_NAME = configForm.textModel.trim()
    if (configForm.solveBaseUrl.trim()) updates.SOLVE_API_BASE_URL = configForm.solveBaseUrl.trim()
    if (configForm.solveKey.trim()) updates.SOLVE_API_KEY = configForm.solveKey.trim()
    if (configForm.solveModel.trim()) updates.SOLVE_MODEL_NAME = configForm.solveModel.trim()

    if (!Object.keys(updates).length) {
      wx.showToast({ title: '没有要更新的配置', icon: 'none' })
      return
    }

    this.setData({ saving: true })

    try {
      const res = await this.request({
        url: `${API_BASE_URL}/api/v1/admin/config`,
        method: 'POST',
        data: updates,
        header: { 'X-Admin-Token': adminToken },
      })

      if (res.success) {
        this.showSaveResult(true, '配置已更新并立即生效')
        this.setData({
          'configForm.visionKey': '',
          'configForm.textKey': '',
          'configForm.solveKey': '',
        })
        await this.loadConfig()
      } else {
        this.showSaveResult(false, res.message || '更新失败')
      }
    } catch (err) {
      this.showSaveResult(false, err.message || '保存失败')
    } finally {
      this.setData({ saving: false })
    }
  },

  showSaveResult(success, message) {
    this.setData({
      saveResult: { show: true, success, message },
    })
    setTimeout(() => {
      this.setData({ 'saveResult.show': false })
    }, 3000)
  },

  async fetchModelList(type) {
    const adminToken = this.getAdminToken()
    if (!adminToken) {
      this.logout()
      return
    }

    const baseUrlKey = `${type}BaseUrl`
    const keyKey = `${type}Key`
    const baseUrl = this.data.configForm[baseUrlKey]
    const apiKey = this.data.configForm[keyKey]

    if (!baseUrl || !apiKey) {
      wx.showToast({ title: '请先填写 Base URL 和 API Key', icon: 'none' })
      return
    }

    this.setData({ [`fetchingModels.${type}`]: true })

    try {
      const res = await this.request({
        url: `${API_BASE_URL}/api/v1/admin/models`,
        method: 'POST',
        data: {
          api_key: apiKey,
          base_url: baseUrl,
        },
        header: { 'X-Admin-Token': adminToken },
      })

      if (res.models && res.models.length > 0) {
        this.setData({
          [`modelLists.${type}`]: res.models,
          [`modelLists.${type}SelectedIndex`]: -1,
          [`modelLists.${type}SelectedDesc`]: '',
        })
      }

      wx.showToast({
        title: res.success ? `获取到${res.models.length}个模型` : (res.message || '获取失败'),
        icon: res.success ? 'success' : 'none',
        duration: 3000,
      })
    } catch (err) {
      wx.showToast({ title: err.message || '请求失败', icon: 'none' })
    } finally {
      this.setData({ [`fetchingModels.${type}`]: false })
    }
  },

  fetchVisionModels() {
    this.fetchModelList('vision')
  },

  fetchTextModels() {
    this.fetchModelList('text')
  },

  fetchSolveModels() {
    this.fetchModelList('solve')
  },

  onVisionModelSelect(e) {
    const index = e.detail.value
    const model = this.data.modelLists.vision[index]
    if (!model) return
    this.setData({
      'configForm.visionModel': model.id,
      'modelLists.visionSelectedIndex': index,
      'modelLists.visionSelectedDesc': model.description || '',
    })
  },

  onTextModelSelect(e) {
    const index = e.detail.value
    const model = this.data.modelLists.text[index]
    if (!model) return
    this.setData({
      'configForm.textModel': model.id,
      'modelLists.textSelectedIndex': index,
      'modelLists.textSelectedDesc': model.description || '',
    })
  },

  onSolveModelSelect(e) {
    const index = e.detail.value
    const model = this.data.modelLists.solve[index]
    if (!model) return
    this.setData({
      'configForm.solveModel': model.id,
      'modelLists.solveSelectedIndex': index,
      'modelLists.solveSelectedDesc': model.description || '',
    })
  },

  async testConnection() {
    const adminToken = this.getAdminToken()
    if (!adminToken) {
      this.logout()
      return
    }

    this.setData({ testing: true })

    try {
      const res = await this.request({
        url: `${API_BASE_URL}/api/v1/admin/config/test`,
        header: { 'X-Admin-Token': adminToken },
      })

      const visionOk = !!(res.details && res.details.vision && res.details.vision.configured)
      const textOk = !!(res.details && res.details.text && res.details.text.configured)
      const solveOk = !!(res.details && res.details.solve && res.details.solve.configured)

      this.setData({
        aiStatus: {
          vision: visionOk,
          text: textOk,
          solve: solveOk,
        }
      })

      wx.showToast({
        title: (visionOk || textOk) ? '配置检查通过' : '配置不完整',
        icon: (visionOk || textOk) ? 'success' : 'none',
      })
    } catch (err) {
      wx.showToast({ title: err.message || '测试失败', icon: 'none' })
    } finally {
      this.setData({ testing: false })
    }
  },

  request({ url, method = 'GET', data = null, header = {} }) {
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
        fail: () => reject(new Error('网络请求失败')),
      })
    })
  },
})
