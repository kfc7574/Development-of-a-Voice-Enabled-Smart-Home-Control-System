package com.example.myapplication.network

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.net.URL

object RetrofitInstance {

    private const val FALLBACK_BASE_URL = "http://10.0.2.2:3000/" // 模擬器用
    private const val LIGHT_CONTROL_URL = "http://172.20.10.13:5000/"

    // 掃描後端 server 的邏輯
    private fun findServer(): String {
        val baseIps = listOf("192.168.0", "192.168.1", "172.20.10")
        for (base in baseIps) {
            for (i in 1..255) {
                val url = "http://$base.$i:3000/ping"
                try {
                    val response = URL(url).readText()
                    if ("pong" in response) {
                        println("✅ 找到 Flask 伺服器：$url")
                        return "http://$base.$i:3000/"
                    }
                } catch (_: Exception) {
                    continue
                }
            }
        }
        println("❌ 找不到 Flask server，改用 fallback：$FALLBACK_BASE_URL")
        return FALLBACK_BASE_URL
    }

    private val BASE_URL: String by lazy {
        findServer() // 啟動時只跑一次
    }

    val api: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }

    val lightApi: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(LIGHT_CONTROL_URL) // 控燈那組 IP 還是寫死沒關係
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}
