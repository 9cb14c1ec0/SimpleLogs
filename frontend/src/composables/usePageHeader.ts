import { reactive } from 'vue'

/**
 * The app bar renders the active view's title, so views own their own heading
 * instead of repeating one inside the page body.
 */
export const pageHeader = reactive({
  title: '',
  meta: '',
  back: '',
})

export function resetPageHeader() {
  pageHeader.title = ''
  pageHeader.meta = ''
  pageHeader.back = ''
}
