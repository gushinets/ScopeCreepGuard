function calendarDay(value: string): number {
  const [year, month, day] = value.split('-').map(Number)
  return Date.UTC(year, month - 1, day) / 86_400_000
}

export function projectTiming(startDate: string, endDate: string | undefined, draftCreatedAt: string) {
  const creationDate = draftCreatedAt.slice(0, 10)
  const calculationEndDate = endDate || creationDate
  return {
    calculationEndDate,
    endDateSource: endDate ? 'explicit' as const : 'draft' as const,
    durationDays: calendarDay(calculationEndDate) - calendarDay(startDate),
    elapsedDays: calendarDay(creationDate) - calendarDay(startDate),
  }
}
