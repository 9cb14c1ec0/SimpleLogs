<template>
  <div>
    <v-card max-width="720" :loading="loading">
      <v-card-text>
        <v-switch
          v-model="form.enabled"
          label="Allow sign-in with SSO"
          color="primary"
          hide-details
          class="mb-4"
        />

        <v-text-field
          v-model="form.issuer"
          label="Issuer URL"
          placeholder="https://sso.example.com/application/o/simplelogs/"
          hint="Shown on the provider's page in Authentik."
          persistent-hint
          class="mb-2"
        />
        <v-text-field v-model="form.client_id" label="Client ID" />
        <v-text-field
          v-model="form.client_secret"
          label="Client secret"
          type="password"
          autocomplete="new-password"
          :hint="hasClientSecret ? 'Leave blank to keep the saved secret.' : ''"
          persistent-hint
        />

        <div class="text-subtitle-2 mt-6 mb-2">Enter these in your SSO provider</div>
        <v-text-field
          :model-value="redirectUri"
          label="Redirect URI"
          readonly
          append-inner-icon="mdi-content-copy"
          @click:append-inner="copy(redirectUri)"
        />
        <v-text-field
          :model-value="launchUrl"
          label="Launch URL"
          readonly
          append-inner-icon="mdi-content-copy"
          @click:append-inner="copy(launchUrl)"
        />

        <v-alert v-if="error" type="error" class="mt-2">{{ error }}</v-alert>
        <v-alert v-if="saved" type="success" class="mt-2">Saved.</v-alert>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn color="primary" :loading="saving" @click="save">Save</v-btn>
      </v-card-actions>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import api, { type SsoSettings } from '@/api/client'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const saved = ref(false)
const hasClientSecret = ref(false)
const redirectUri = ref('')
const launchUrl = ref('')

const form = reactive({
  enabled: false,
  issuer: '',
  client_id: '',
  client_secret: '',
})

onMounted(async () => {
  loading.value = true
  try {
    const response = await api.get<SsoSettings>('/admin/sso')
    applySettings(response.data)
  } catch (e) {
    console.error('Failed to load SSO settings:', e)
    error.value = "Couldn't load the SSO settings."
  } finally {
    loading.value = false
  }
})

function applySettings(settings: SsoSettings) {
  form.enabled = settings.enabled
  form.issuer = settings.issuer
  form.client_id = settings.client_id
  form.client_secret = ''
  hasClientSecret.value = settings.has_client_secret
  redirectUri.value = settings.redirect_uri
  launchUrl.value = settings.launch_url
}

async function save() {
  error.value = ''
  saved.value = false
  saving.value = true
  try {
    const response = await api.put<SsoSettings>('/admin/sso', form)
    applySettings(response.data)
    saved.value = true
  } catch (e: any) {
    error.value = e.response?.data?.detail ?? "Couldn't save the SSO settings."
  } finally {
    saving.value = false
  }
}

function copy(text: string) {
  navigator.clipboard.writeText(text)
}
</script>
