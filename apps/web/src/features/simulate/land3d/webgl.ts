/** True when the browser can draw WebGL (false in tests/jsdom, so the 2D illustration is used there). */
export function hasWebGL(): boolean {
  if (
    typeof window === 'undefined' ||
    typeof navigator === 'undefined' ||
    /jsdom/i.test(navigator.userAgent)
  )
    return false;
  try {
    const canvas = document.createElement('canvas');
    return Boolean(canvas.getContext('webgl2') ?? canvas.getContext('webgl'));
  } catch {
    return false;
  }
}
