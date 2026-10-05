// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest'
import { readProjectDetails, writeProjectDetails } from './browser-details'

beforeEach(() => localStorage.clear())

describe('optional project details', () => {
  it('stays in browser storage and is scoped to user and project', () => {
    writeProjectDetails('u1', 'p1', { clientName: 'Acme', clientEmail: 'a@b.test', endDate: '2026-11-01' })
    expect(readProjectDetails('u1', 'p1').clientName).toBe('Acme')
    expect(readProjectDetails('u2', 'p1')).toEqual({ clientName: '', clientEmail: '', endDate: '' })
    expect(readProjectDetails('u1', 'p2')).toEqual({ clientName: '', clientEmail: '', endDate: '' })
  })

  it('ignores malformed saved data', () => {
    localStorage.setItem('scg:project:u1:p1', 'bad json')
    expect(readProjectDetails('u1', 'p1').endDate).toBe('')
  })

  it('remains usable when browser storage is unavailable', () => {
    const original = Object.getOwnPropertyDescriptor(window, 'localStorage')
    Object.defineProperty(window, 'localStorage', { configurable: true, get: () => { throw new Error('disabled') } })
    try {
      expect(readProjectDetails('u1', 'p1')).toEqual({ clientName: '', clientEmail: '', endDate: '' })
      expect(() => writeProjectDetails('u1', 'p1', { clientName: 'Acme', clientEmail: '', endDate: '' })).not.toThrow()
    } finally {
      if (original) Object.defineProperty(window, 'localStorage', original)
    }
  })
})
