// app.js
const STUDENT_PROFILE_KEY = 'student_profile'

App({
  onLaunch() {
    console.log('AI数学作业批改小程序启动')

    try {
      const cachedProfile = wx.getStorageSync(STUDENT_PROFILE_KEY)
      if (cachedProfile && cachedProfile.nickName) {
        this.globalData.studentProfile = cachedProfile
      }
    } catch (err) {
      console.warn('读取本地登录态失败:', err)
    }
  },

  globalData: {
    // 云托管生产环境
    apiBaseUrl: 'https://math-api-234234-9-1324601200.sh.run.tcloudbase.com',
    studentProfile: null,
  }
})
