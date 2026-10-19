import { useEffect, useId } from "react";
import i18n from "./i18n";

/**
 * Asks before unsaved edits are dropped. The app runs on <BrowserRouter>, where
 * React Router's useBlocker isn't available (it needs a data router), so this covers
 * the ways a page with edits goes away:
 *  - reloading or closing the tab: the browser's own prompt (beforeunload);
 *  - a click on a link to another page of the app (menus, "All templates", …): a confirm;
 *  - an in-page change that unmounts the edits (another class, tab, …): the page calls
 *    confirmLeave() before making it.
 * A component with edits calls useUnsavedChanges(dirty); one prompt covers all of them.
 * Browser Back/Forward can't be stopped this way.
 */
const dirtyOwners = new Set<string>();

/** The SPA's path prefix without the trailing slash ("" when served at the root). */
const APP_BASE = (import.meta.env.BASE_URL || "/").replace(/\/+$/, "");

function leaveMessage(): string {
  return i18n.t("portal.common.unsavedLeaveConfirm", "You have unsaved changes. Leave without saving them?");
}

/** True while some page has edits that aren't saved (the post-deploy reload waits for them). */
export function hasUnsavedChanges(): boolean {
  return dirtyOwners.size > 0;
}

/** True when nothing is unsaved, or the person agreed to drop it. */
export function confirmLeave(): boolean {
  return dirtyOwners.size === 0 || window.confirm(leaveMessage());
}

function onBeforeUnload(e: BeforeUnloadEvent) {
  e.preventDefault();
  e.returnValue = ""; // some browsers still need it set to show the prompt
}

/** Capture phase on document, so it runs before React Router's <Link> click handler. */
function onLinkClick(e: MouseEvent) {
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  const link = e.target instanceof Element ? e.target.closest("a[href]") : null;
  if (!(link instanceof HTMLAnchorElement) || link.hasAttribute("download")) return;
  if (link.target && link.target !== "_self") return;
  const to = new URL(link.href);
  const inApp = !APP_BASE || to.pathname === APP_BASE || to.pathname.startsWith(`${APP_BASE}/`);
  // Leaving the app is a full page load, which beforeunload already asks about.
  if (to.origin !== window.location.origin || !inApp) return;
  if (to.pathname === window.location.pathname && to.search === window.location.search) return;
  if (!window.confirm(leaveMessage())) {
    e.preventDefault();
    e.stopPropagation();
  }
}

function syncListeners() {
  if (dirtyOwners.size) {
    window.addEventListener("beforeunload", onBeforeUnload);
    document.addEventListener("click", onLinkClick, true);
  } else {
    window.removeEventListener("beforeunload", onBeforeUnload);
    document.removeEventListener("click", onLinkClick, true);
  }
}

/** While `dirty`, reloading, following an in-app link or confirmLeave() asks first. */
export function useUnsavedChanges(dirty: boolean): void {
  const owner = useId();
  useEffect(() => {
    if (!dirty) return;
    dirtyOwners.add(owner);
    syncListeners();
    return () => {
      dirtyOwners.delete(owner);
      syncListeners();
    };
  }, [dirty, owner]);
}
