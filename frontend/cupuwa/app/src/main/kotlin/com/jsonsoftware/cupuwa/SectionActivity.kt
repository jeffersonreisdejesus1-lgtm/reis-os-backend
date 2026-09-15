package com.jsonsoftware.cupuwa

import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class SectionActivity : AppCompatActivity() {
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        setContentView(R.layout.activity_section)
        val section = intent.getStringExtra(EXTRA_SECTION) ?: PLAN
        findViewById<TextView>(R.id.sectionTitle).text = if (section == SETTINGS) getString(R.string.section_settings) else getString(R.string.section_plan)
        findViewById<TextView>(R.id.sectionBody).text = if (section == SETTINGS) getString(R.string.section_settings_body) else getString(R.string.section_plan_body)
    }
    companion object { const val EXTRA_SECTION = "section"; const val PLAN = "plan"; const val SETTINGS = "settings" }
}

