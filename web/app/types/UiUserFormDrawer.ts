import type { User, UserRole } from '~/types'
import type { UserFormDrawerMode } from '~/types/DrawerStack'
import type { UiDrawerProps } from '~/types/UiDrawer'

export type UiUserFormDrawerProps = UiDrawerProps & {
  mode?: UserFormDrawerMode
  user?: User | null
}

/** Local shape of the user form (password only ever filled on creation). */
export type UserForm = {
  name: string
  email: string
  password: string
  role: UserRole
}

export type UiUserFormDrawerEmits = {
  close: []
  back: []
  saved: [user: User]
}
