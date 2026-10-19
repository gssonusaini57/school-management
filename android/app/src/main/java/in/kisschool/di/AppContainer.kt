package `in`.kisschool.di

import android.content.Context
import android.os.Build
import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.auth.AccountStore
import `in`.kisschool.data.auth.AppLockController
import `in`.kisschool.data.auth.LoginHandoff
import `in`.kisschool.data.auth.SecurePrefs
import `in`.kisschool.data.auth.SessionManager
import `in`.kisschool.data.auth.TokenAuthenticator
import `in`.kisschool.data.auth.TokenStore
import `in`.kisschool.data.repo.AdminRepository
import `in`.kisschool.data.repo.AppUpdateRepository
import `in`.kisschool.data.repo.AttendanceRepository
import `in`.kisschool.data.repo.AuthRepository
import `in`.kisschool.data.repo.DashboardRepository
import `in`.kisschool.data.repo.MarksRepository
import `in`.kisschool.data.repo.MetaRepository
import `in`.kisschool.data.repo.NoticeRepository
import `in`.kisschool.data.repo.ReportCardRepository
import `in`.kisschool.data.repo.ResultsRepository
import `in`.kisschool.data.repo.SessionRepository
import `in`.kisschool.data.repo.StudentRepository
import `in`.kisschool.data.settings.SettingsStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

class AppContainer(context: Context) {

    /**
     * Emitted when the active session is gone for good: the API answered 401 and the
     * silent refresh was refused (or there was nothing to refresh with). The UI routes
     * back to Login; the accounts saved on the phone stay.
     */
    val authExpired = MutableSharedFlow<Unit>(extraBufferCapacity = 1)

    /** Background work that must outlive a screen: telling the server about a logout. */
    val appScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private val securePrefs = SecurePrefs.open(context.applicationContext)

    val tokenStore = TokenStore(securePrefs)

    /** The accounts saved on this phone (same encrypted file as the session). */
    val accounts = AccountStore(securePrefs)

    /** App settings (theme, app lock); plain prefs, read by MainActivity and Settings. */
    val settings = SettingsStore(context.applicationContext)

    /** Prefill + notice for the next login screen (after an expired session, say). */
    val loginHandoff = LoginHandoff()

    /** Locked / unlocked state behind the fingerprint-face-PIN gate (ui/lock). */
    val appLock = AppLockController(settings, accounts, tokenStore)

    private fun baseClient(): OkHttpClient.Builder = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)

    // Log only at body level in debug; release builds get NONE so we never leak tokens.
    private fun OkHttpClient.Builder.withLogging(): OkHttpClient.Builder = apply {
        val level = if (BuildConfigBridge.isDebug) HttpLoggingInterceptor.Level.BASIC
        else HttpLoggingInterceptor.Level.NONE
        addInterceptor(HttpLoggingInterceptor().setLevel(level))
    }

    private fun retrofit(client: OkHttpClient): Retrofit = Retrofit.Builder()
        // Per-flavor base URL (prod → kisschool.in, test → 69.62.72.137/kisschool),
        // injected via buildConfigField in app/build.gradle.kts.
        .baseUrl(`in`.kisschool.BuildConfig.API_BASE_URL)
        .client(client)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    /**
     * The API over a bare client: no Bearer header, no authenticator. Only the session
     * manager uses it, for POST /auth/refresh, which must never trigger another refresh.
     */
    private val authApi: ApiService = retrofit(baseClient().withLogging().build()).create(ApiService::class.java)

    val sessionManager: SessionManager = SessionManager(
        api = authApi,
        tokenStore = tokenStore,
        accounts = accounts,
        onSessionLost = { lost ->
            loginHandoff.post(lost?.identifier, lost?.let { LoginHandoff.EXPIRED_NOTICE })
            authRepo.onSessionLost()
            authExpired.tryEmit(Unit)
        },
    )

    /**
     * The app's HTTP client: adds the Bearer header, and on a 401 refreshes the session
     * once and retries (see [TokenAuthenticator]). Shared with Coil (KisApp), so student
     * document images are fetched with the same header instead of a token in the URL.
     */
    val httpClient: OkHttpClient = baseClient()
        .addInterceptor { chain ->
            val req = chain.request()
            val token = tokenStore.token
            val authed = if (token.isNullOrBlank()) req
            else req.newBuilder().header("Authorization", "Bearer $token").build()
            chain.proceed(authed)
        }
        .authenticator(TokenAuthenticator(sessionManager))
        .withLogging()
        .build()

    private val retrofit: Retrofit = retrofit(httpClient)

    val api: ApiService = retrofit.create(ApiService::class.java)

    // Same client (auth + refresh-and-retry + logging) with a longer read timeout, for
    // report-card renders and PDF downloads: a first render can outlast 30 s.
    private val renderApi: ApiService = retrofit.newBuilder()
        .client(httpClient.newBuilder().readTimeout(120, TimeUnit.SECONDS).build())
        .build()
        .create(ApiService::class.java)

    val authRepo: AuthRepository = AuthRepository(
        api = api,
        tokenStore = tokenStore,
        accounts = accounts,
        sessions = sessionManager,
        appScope = appScope,
        deviceName = deviceName(),
    )
    val studentRepo = StudentRepository(api)
    val attendanceRepo = AttendanceRepository(api)
    val marksRepo = MarksRepository(api)
    val appUpdateRepo = AppUpdateRepository(api)
    val adminRepo = AdminRepository(api)
    val sessionRepo = SessionRepository(api)
    val metaRepo = MetaRepository(api)
    val resultsRepo = ResultsRepository(api)
    val noticeRepo = NoticeRepository(api)
    val dashboardRepo = DashboardRepository(api)
    val reportCardRepo = ReportCardRepository(
        api = api,
        renderApi = renderApi,
        cacheDir = context.applicationContext.cacheDir,
    )

    /** "Samsung SM-A125F": the manufacturer and model, as GET /auth/sessions shows this phone. */
    private fun deviceName(): String {
        val parts = listOf(Build.MANUFACTURER, Build.MODEL).map { it?.trim().orEmpty() }.filter { it.isNotEmpty() }
        return parts.joinToString(" ").replaceFirstChar { it.uppercase() }.take(120)
    }
}

/** Tiny indirection so we can read BuildConfig.DEBUG without importing it everywhere. */
internal object BuildConfigBridge {
    val isDebug: Boolean = `in`.kisschool.BuildConfig.DEBUG
}
