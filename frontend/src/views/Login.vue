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
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const totpCode = ref('')
const error = ref('')
const loading = ref(false)

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
