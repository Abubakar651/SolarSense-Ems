/** Reads a text input's value from a submitted form; '' when the field is missing. */
export function fieldValue(form: HTMLFormElement, name: string): string {
  const element = form.elements.namedItem(name);
  return element instanceof HTMLInputElement ? element.value : '';
}

export function checkboxValue(form: HTMLFormElement, name: string): boolean {
  const element = form.elements.namedItem(name);
  return element instanceof HTMLInputElement && element.checked;
}
