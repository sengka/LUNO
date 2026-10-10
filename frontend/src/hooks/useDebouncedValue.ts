import { useEffect, useState } from 'react'

// Değer değişmeyi bıraktıktan belli bir süre sonra güncellenir (ör. her tuşta değil, yazma bitince ara)
export function useDebouncedValue<T>(value: T, delayMs = 300) {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return debounced
}
