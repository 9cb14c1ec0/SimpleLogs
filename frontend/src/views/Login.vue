<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="4">
        <v-card class="elevation-12">
          <v-toolbar color="primary" dark flat>
            <v-toolbar-title>SimpleLogs</v-toolbar-title>
          </v-toolbar>

          <!-- Phase 1: Email/Password -->
          <template v-if="!authStore.totpRequired">
            <v-card-text>
              <v-form @submit.prevent="handleLogin">
                <v-text-field
                  v-model="email"
                  label="Email"
                  type="email"
                  prepend-icon="mdi-email"
                  required
                  :disabled="loading"
                />

                <v-text-field
                  v-model="password"
                  label="Password"
                  type="password"
                  prepend-icon="mdi-lock"
                  required
                  :disabled="loading"
                />

                <v-alert v-if="error" type="error" class="mt-4">
                  {{ error }}
                </v-alert>
              </v-form>
            </v-card-text>

            <v-card-actions>
              <v-btn
                variant="outlined"
                prepend-icon="mdi-fingerprint"
                :disabled="loading"
                @click="handlePasskeyLogin"
              >
                Sign in with passkey
              </v-btn>
              <v-spacer />
              <v-btn
                color="primary"
                :loading="loading"
                @click="handleLogin"
              >
                Login
              </v-btn>
            </v-card-actions>

            <v-card-actions v-if="ssoEnabled" class="pt-0">
              <v-btn
                block
                variant="tonal"
                color="primary"
                prepend-icon="mdi-shield-account"
                href="/api/v1/auth/sso/login"
                :disabled="loading"
              >
                Sign in with SSO
              </v-btn>
            </v-card-actions>
          </template>

          <!-- Phase 2: TOTP Code -->
          <template v-else>
            <v-card-text>
              <v-form @submit.prevent="handleTotp">
                <p class="text-body-2 mb-4">
                  Enter the 6-digit code from your authenticator app, or a recovery code.
                </p>

                <v-text-field
                  v-model="totpCode"
                  label="Authentication Code"
                  prepend-icon="mdi-shield-key"
                  required
                  autofocus
                  :disabled="loading"
                />

                <v-alert v-if="error" type="error" class="mt-4">
                  {{ error }}
                </v-alert>
              </v-form>
            </v-card-text>

            <v-card-actions>
              <v-btn @click="handleBack">
                Back
              </v-btn>
              <v-spacer />
              <v-btn
                color="primary"
                :loading="loading"
                @click="handleTotp"
              >
                Verify
              </v-btn>
            </v-card-actions>
          </template>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const totpCode = ref('')
const error = ref('')
const loading = ref(false)
const ssoEnabled = ref(false)

const ssoErrors: Record<string, string> = {
  no_account: "There's no SimpleLogs account for your SSO email.",
  disabled: 'Your SimpleLogs account is disabled.',
  failed: "SSO sign-in didn't work. Please try again.",
}

onMounted(async () => {
  const ssoError = route.query.sso_error
  if (typeof ssoError === 'string') {
    error.value = ssoErrors[ssoError] ?? ssoErrors.failed
    router.replace({ query: {} })
  }

  // The SSO callback lands here with the tokens in the URL fragment
  const fragment = new URLSearchParams(window.location.hash.slice(1))
  const accessToken = fragment.get('access_token')
  const refreshToken = fragment.get('refresh_token')
  if (accessToken && refreshToken) {
    history.replaceState(history.state, '', window.location.pathname)
    loading.value = true
    if (await authStore.loginWithTokens(accessToken, refreshToken)) {
      router.push('/')
      return
    }
    error.value = ssoErrors.failed
    loading.value = false
  }

  try {
    const response = await api.get<{ enabled: boolean }>('/auth/sso/config')
    ssoEnabled.value = response.data.enabled
  } catch {
    ssoEnabled.value = false
  }
})

async function handleLogin() {
  error.value = ''
  loading.value = true

  const result = await authStore.login(email.value, password.value)

  if (result === 'success') {
    router.push('/')
  } else if (result === 'totp_required') {
    // Phase 2 will show automatically via authStore.totpRequired
  } else {
    error.value = 'Invalid email or password'
  }

  loading.value = false
}

async function handleTotp() {
  error.value = ''
  loading.value = true

  const success = await authStore.verifyTotp(totpCode.value)

  if (success) {
    router.push('/')
  } else {
    error.value = 'Invalid authentication code'
  }

  loading.value = false
}

async function handlePasskeyLogin() {
  error.value = ''
  loading.value = true

  const result = await authStore.loginWithPasskey()

  if (result === 'success') {
    router.push('/')
  } else if (result === 'error') {
    error.value = 'Passkey authentication failed'
  }

  loading.value = false
}

function handleBack() {
  authStore.clearTotpState()
  totpCode.value = ''
  error.value = ''
}
</script>
