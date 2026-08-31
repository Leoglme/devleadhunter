/** A tool module and whether it is active for the user. */
export type ModuleState = {
  module: string
  active: boolean
}

/** The user's activation state for every module (`GET /modules`). */
export type ModulesResponse = {
  modules: ModuleState[]
}
