/** Preferences/recovery adapters; confirmed application data stays on the server. */
export const recoveryStorage = {
  get: (key: string) => localStorage.getItem(key),
  set: (key: string, value: string) => localStorage.setItem(key, value),
  remove: (key: string) => localStorage.removeItem(key),
  keys: () => Object.keys(localStorage),
}
export const tabStorage = {
  get: (key: string) => sessionStorage.getItem(key),
  set: (key: string, value: string) => sessionStorage.setItem(key, value),
}
