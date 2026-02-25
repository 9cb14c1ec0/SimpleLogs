<template>
  <div>
    <h1 class="text-h4 mb-4">Settings</h1>

    <v-card max-width="600">
      <v-card-title>Two-Factor Authentication</v-card-title>
      <v-card-text>
        <v-chip :color="authStore.user?.totp_enabled ? 'success' : 'grey'" class="mb-4">
          {{ authStore.user?.totp_enabled ? '2FA Enabled' : '2FA Disabled' }}
        </v-chip>

        <p v-if="!authStore.user?.totp_enabled" class="text-body-2">
          Add an extra layer of security to your account by enabling two-factor authentication.
        </p>
        <p v-else class="text-body-2">
          Two-factor authentication is active. You will need your authenticator app or a recovery code to log in.
        </p>
      </v-card-text>
      <v-card-actions>
        <v-btn
          v-if="!authStore.user?.totp_enabled"
          color="primary"
          @click="beginSetup"
          :loading="setupLoading"
        >
          Enable 2FA
        </v-btn>
        <v-btn
          v-else
          color="error"
          variant="outlined"
          @click="disableDialog = true"
        >
          Disable 2FA
        </v-btn>
      </v-card-actions>
    </v-card>

    <!-- Passkeys Card -->
    <v-card max-width="600" class="mt-6">
      <v-card-title>Passkeys</v-card-title>
      <v-card-text>
        <p class="text-body-2 mb-4">
          Passkeys let you sign in with your fingerprint, face, or security key — no password needed.
        </p>

        <v-list v-if="passkeys.length > 0" density="compact">
          <v-list-item v-for="pk in passkeys" :key="pk.id">
            <template #prepend>
              <v-icon>mdi-fingerprint</v-icon>
            </template>
            <v-list-item-title>{{ pk.name }}</v-list-item-title>
            <v-list-item-subtitle>
              Created {{ new Date(pk.created_at).toLocaleDateString() }}
              <template v-if="pk.last_used_at">
                · Last used {{ new Date(pk.last_used_at).toLocaleDateString() }}
              </template>
            </v-list-item-subtitle>
            <template #append>
              <v-btn icon="mdi-delete" variant="text" size="small" @click="confirmDeletePasskey(pk)" />
            </template>
          </v-list-item>
        </v-list>
        <p v-else class="text-body-2 text-medium-emphasis">No passkeys registered yet.</p>
      </v-card-text>
      <v-card-actions>
        <v-btn color="primary" @click="passkeyNameDialog = true" :loading="passkeyRegisterLoading">
          Register new passkey
        </v-btn>
      </v-card-actions>
    </v-card>

    <!-- Passkey Name Dialog -->
    <v-dialog v-model="passkeyNameDialog" max-width="400">
      <v-card>
        <v-card-title>Register Passkey</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="registerPasskey">
            <v-text-field
              v-model="passkeyName"
              label="Passkey name"
              placeholder="e.g. MacBook fingerprint"
              autofocus
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="passkeyNameDialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="passkeyRegisterLoading" @click="registerPasskey">Register</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Passkey Delete Confirmation Dialog -->
    <v-dialog v-model="passkeyDeleteDialog" max-width="400">
      <v-card>
        <v-card-title>Delete Passkey</v-card-title>
        <v-card-text>
          Are you sure you want to delete "{{ passkeyToDelete?.name }}"? You will no longer be able to sign in with this passkey.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="passkeyDeleteDialog = false">Cancel</v-btn>
          <v-btn color="error" :loading="passkeyDeleteLoading" @click="deletePasskey">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Setup Dialog -->
    <v-dialog v-model="setupDialog" max-width="500" persistent>
      <v-card>
        <v-card-title>Enable Two-Factor Authentication</v-card-title>

        <!-- Step 1: QR Code -->
        <template v-if="setupStep === 1">
          <v-card-text>
            <p class="text-body-2 mb-4">
              Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.).
            </p>
            <div class="d-flex justify-center mb-4">
              <img :src="setupData?.qr_code" alt="TOTP QR Code" style="max-width: 200px;" />
            </div>
            <p class="text-body-2 mb-2">Or enter this secret manually:</p>
            <v-text-field
              :model-value="setupData?.secret"
              readonly
              variant="outlined"
              density="compact"
              append-inner-icon="mdi-content-copy"
              @click:append-inner="copyToClipboard(setupData?.secret || '')"
            />
          </v-card-text>
          <v-card-actions>
            <v-btn @click="cancelSetup">Cancel</v-btn>
            <v-spacer />
            <v-btn color="primary" @click="setupStep = 2">Next</v-btn>
          </v-card-actions>
        </template>

        <!-- Step 2: Verify Code -->
        <template v-if="setupStep === 2">
          <v-card-text>
            <p class="text-body-2 mb-4">
              Enter the 6-digit code from your authenticator app to verify setup.
            </p>
            <v-form @submit.prevent="verifySetup">
              <v-text-field
                v-model="verifyCode"
                label="Authentication Code"
                autofocus
                :error-messages="setupError"
              />
            </v-form>
          </v-card-text>
          <v-card-actions>
            <v-btn @click="setupStep = 1">Back</v-btn>
            <v-spacer />
            <v-btn color="primary" :loading="verifyLoading" @click="verifySetup">Verify</v-btn>
          </v-card-actions>
        </template>

        <!-- Step 3: Recovery Codes -->
        <template v-if="setupStep === 3">
          <v-card-text>
            <v-alert type="warning" class="mb-4">
              Save these recovery codes in a safe place. Each code can only be used once.
              You will not be able to see them again.
            </v-alert>
            <v-card variant="outlined" class="pa-3 mb-4">
              <div class="d-flex flex-wrap ga-2">
                <code v-for="code in setupData?.recovery_codes" :key="code" class="pa-1">
                  {{ code }}
                </code>
              </div>
            </v-card>
            <v-btn
              variant="outlined"
              size="small"
              prepend-icon="mdi-content-copy"
              @click="copyToClipboard(setupData?.recovery_codes?.join('\n') || '')"
            >
              Copy All
            </v-btn>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn color="primary" @click="finishSetup">Done</v-btn>
          </v-card-actions>
        </template>
      </v-card>
    </v-dialog>

    <!-- Disable Dialog -->
    <v-dialog v-model="disableDialog" max-width="400">
      <v-card>
        <v-card-title>Disable Two-Factor Authentication</v-card-title>
        <v-card-text>
          <p class="text-body-2 mb-4">Enter your password to confirm disabling 2FA.</p>
          <v-form @submit.prevent="disableTotp">
            <v-text-field
              v-model="disablePassword"
              label="Password"
              type="password"
              autofocus
              :error-messages="disableError"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="disableDialog = false">Cancel</v-btn>
          <v-btn color="error" :loading="disableLoading" @click="disableTotp">Disable</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar -->
    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarMessage }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { startRegistration } from '@simplewebauthn/browser'
import api, { type TOTPSetupResponse, type PasskeyCredential } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const setupDialog = ref(false)
const setupStep = ref(1)
const setupData = ref<TOTPSetupResponse | null>(null)
const setupLoading = ref(false)
const setupError = ref('')
const verifyCode = ref('')
const verifyLoading = ref(false)

const disableDialog = ref(false)
const disablePassword = ref('')
const disableLoading = ref(false)
const disableError = ref('')

const snackbar = ref(false)
const snackbarMessage = ref('')
const snackbarColor = ref('success')

function showSnackbar(message: string, color = 'success') {
  snackbarMessage.value = message
  snackbarColor.value = color
  snackbar.value = true
}

async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    showSnackbar('Copied to clipboard')
  } catch {
    showSnackbar('Failed to copy', 'error')
  }
}

async function beginSetup() {
  setupLoading.value = true
  try {
    const response = await api.post<TOTPSetupResponse>('/auth/totp/setup')
    setupData.value = response.data
    setupStep.value = 1
    verifyCode.value = ''
    setupError.value = ''
    setupDialog.value = true
  } catch {
    showSnackbar('Failed to start 2FA setup', 'error')
  } finally {
    setupLoading.value = false
  }
}

function cancelSetup() {
  setupDialog.value = false
  setupData.value = null
}

async function verifySetup() {
  setupError.value = ''
  verifyLoading.value = true
  try {
    await api.post('/auth/totp/setup/verify', { code: verifyCode.value })
    setupStep.value = 3
    await authStore.fetchUser()
  } catch {
    setupError.value = 'Invalid code. Please try again.'
  } finally {
    verifyLoading.value = false
  }
}

function finishSetup() {
  setupDialog.value = false
  setupData.value = null
  showSnackbar('Two-factor authentication enabled')
}

async function disableTotp() {
  disableError.value = ''
  disableLoading.value = true
  try {
    await api.post('/auth/totp/disable', { password: disablePassword.value })
    disableDialog.value = false
    disablePassword.value = ''
    await authStore.fetchUser()
    showSnackbar('Two-factor authentication disabled')
  } catch {
    disableError.value = 'Invalid password'
  } finally {
    disableLoading.value = false
  }
}

// --- Passkeys ---

const passkeys = ref<PasskeyCredential[]>([])
const passkeyNameDialog = ref(false)
const passkeyName = ref('Passkey')
const passkeyRegisterLoading = ref(false)
const passkeyDeleteDialog = ref(false)
const passkeyToDelete = ref<PasskeyCredential | null>(null)
const passkeyDeleteLoading = ref(false)

async function loadPasskeys() {
  try {
    const response = await api.get<PasskeyCredential[]>('/auth/passkeys')
    passkeys.value = response.data
  } catch {
    // ignore
  }
}

async function registerPasskey() {
  passkeyRegisterLoading.value = true
  try {
    const optionsResp = await api.post('/auth/passkeys/register/options')
    const options = JSON.parse(optionsResp.data.options)

    let credential
    try {
      credential = await startRegistration({ optionsJSON: options })
    } catch {
      passkeyNameDialog.value = false
      passkeyRegisterLoading.value = false
      return
    }

    await api.post('/auth/passkeys/register/verify', {
      credential: JSON.stringify(credential),
      name: passkeyName.value || 'Passkey',
    })

    passkeyNameDialog.value = false
    passkeyName.value = 'Passkey'
    await loadPasskeys()
    showSnackbar('Passkey registered successfully')
  } catch {
    showSnackbar('Failed to register passkey', 'error')
  } finally {
    passkeyRegisterLoading.value = false
  }
}

function confirmDeletePasskey(pk: PasskeyCredential) {
  passkeyToDelete.value = pk
  passkeyDeleteDialog.value = true
}

async function deletePasskey() {
  if (!passkeyToDelete.value) return
  passkeyDeleteLoading.value = true
  try {
    await api.delete(`/auth/passkeys/${passkeyToDelete.value.id}`)
    passkeyDeleteDialog.value = false
    passkeyToDelete.value = null
    await loadPasskeys()
    showSnackbar('Passkey deleted')
  } catch {
    showSnackbar('Failed to delete passkey', 'error')
  } finally {
    passkeyDeleteLoading.value = false
  }
}

onMounted(() => {
  loadPasskeys()
})
</script>
