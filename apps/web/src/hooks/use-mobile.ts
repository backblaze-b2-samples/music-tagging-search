import * as React from "react"

const MOBILE_BREAKPOINT = 768

const getServerSnapshot = () => false

const getSnapshot = () => window.innerWidth < MOBILE_BREAKPOINT

const subscribe = (callback: () => void) => {
  const mediaQueryList = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
  mediaQueryList.addEventListener("change", callback)
  return () => mediaQueryList.removeEventListener("change", callback)
}

export function useIsMobile() {
  return React.useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}
