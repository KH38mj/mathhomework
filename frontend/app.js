const STUDENT_PROFILE_KEY = 'student_profile'
const STUDENT_SESSION_KEY = 'student_session'

App({
  onLaunch() {
    try {
      const cachedProfile = wx.getStorageSync(STUDENT_PROFILE_KEY)
      if (cachedProfile && cachedProfile.nickName) {
        this.globalData.studentProfile = cachedProfile
      }
    } catch (err) {
      console.warn('Failed to read the cached student profile', err)
    }

    try {
      const cachedSession = wx.getStorageSync(STUDENT_SESSION_KEY)
      if (cachedSession && cachedSession.sessionToken) {
        this.globalData.studentSession = cachedSession
      }
    } catch (err) {
      console.warn('Failed to read the cached student session', err)
    }
  },

  globalData: {
    apiBaseUrl: 'https://math-api-234234-9-1324601200.sh.run.tcloudbase.com',
    studentProfile: null,
    studentSession: null,
  }
})
