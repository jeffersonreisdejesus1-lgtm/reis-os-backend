package com.jsonsoftware.cupuwa

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText

class OnboardingActivity : AppCompatActivity() {
    private lateinit var product: ProductStore

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        setContentView(R.layout.activity_onboarding)
        LedgerMath.configureMoneyInput(findViewById(R.id.openingBalance))
        product = ProductStore(this)
        LedgerMath.configureMoneyInput(findViewById(R.id.openingBalance))
        findViewById<MaterialButton>(R.id.continueButton).setOnClickListener { finishOnboarding() }
        findViewById<MaterialButton>(R.id.skipNameButton).setOnClickListener {
            findViewById<TextInputEditText>(R.id.profileName).setText("")
            finishOnboarding()
        }
    }

    private fun finishOnboarding() {
        val name = findViewById<TextInputEditText>(R.id.profileName).text?.toString()?.trim().orEmpty()
        val accountName = findViewById<TextInputEditText>(R.id.accountName).text?.toString()?.trim().orEmpty()
        val openingText = findViewById<TextInputEditText>(R.id.openingBalance).text?.toString().orEmpty()
        runCatching {
            val opening = LedgerMath.parseCentsAllowZero(openingText.ifBlank { "0" })
            val account = product.saveAccount(accountName, Account.Type.CHECKING, opening)
            product.setActiveAccount(account.id)
            product.saveProfile(LocalProfile(name = name, onboardingComplete = true))
            startActivity(Intent(this, MainActivity::class.java))
            finish()
        }.onFailure {
            Toast.makeText(this, it.message ?: "Confira os dados informados", Toast.LENGTH_LONG).show()
        }
    }
}
