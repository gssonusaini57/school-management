package `in`.kisschool.di

import android.content.Context
import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.auth.TokenStore
import `in`.kisschool.data.repo.AttendanceRepository
import `in`.kisschool.data.repo.AuthRepository
import `in`.kisschool.data.repo.MarksRepository
import `in`.kisschool.data.repo.StudentRepository
import kotlinx.coroutines.flow.MutableSharedFlow
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

class AppContainer(context: Context) {

    /** Emitted whenever the API returns 401, so the UI can route back to Login. */
    val authExpired = MutableSharedFlow<Unit>(extraBufferCapacity = 1)

    val tokenStore = TokenStore(context.applicationContext)

    private val httpClient: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .addInterceptor { chain ->
            val req = chain.request()
            val token = tokenStore.token
            val authed = if (token.isNullOrBlank()) req
            else req.newBuilder().header("Authorization", "Bearer $token").build()
            val resp = chain.proceed(authed)
            if (resp.code == 401) {
                tokenStore.clear()
                authExpired.tryEmit(Unit)
            }
            resp
        }
        .apply {
            // Log only at body level in debug; release builds get NONE so we never leak tokens.
            val level = if (BuildConfigBridge.isDebug) HttpLoggingInterceptor.Level.BASIC
            else HttpLoggingInterceptor.Level.NONE
            addInterceptor(HttpLoggingInterceptor().setLevel(level))
        }
        .build()

    private val retrofit: Retrofit = Retrofit.Builder()
        // Per-flavor base URL (prod → kisschool.in, test → expressonly.in/school),
        // injected via buildConfigField in app/build.gradle.kts.
        .baseUrl(`in`.kisschool.BuildConfig.API_BASE_URL)
        .client(httpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val api: ApiService = retrofit.create(ApiService::class.java)

    val authRepo = AuthRepository(api, tokenStore)
    val studentRepo = StudentRepository(api)
    val attendanceRepo = AttendanceRepository(api)
    val marksRepo = MarksRepository(api)
}

/** Tiny indirection so we can read BuildConfig.DEBUG without importing it everywhere. */
internal object BuildConfigBridge {
    val isDebug: Boolean = `in`.kisschool.BuildConfig.DEBUG
}
