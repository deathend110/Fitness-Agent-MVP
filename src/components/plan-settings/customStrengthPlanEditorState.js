export function shouldDisableCustomStrengthCreate({ canCreate, isSubmitting }) {
  return Boolean(isSubmitting) || !canCreate
}
