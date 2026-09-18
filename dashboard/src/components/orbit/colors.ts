import type { AgentClass, DomainKey } from '../../types/system'

export const CLASS_COLOR: Record<AgentClass, string> = {
  CEO: 'var(--violet)',
  Research: 'var(--cyan)',
  Market: 'var(--cyan)',
  Experiment: 'var(--magenta)',
  Content: 'var(--magenta)',
  Affiliate: 'var(--magenta)',
  Sales: 'var(--magenta)',
  Finance: 'var(--gold)',
  RiskManager: 'var(--red)',
  Learning: 'var(--green)',
  Factory: 'var(--amber)',
  DigitalProduct: 'var(--gold)',
}

/** Solid hexes (no CSS var) for SVG fill / stroke. */
export const CLASS_HEX: Record<AgentClass, string> = {
  CEO: '#8B5CF6',
  Research: '#00B4D8',
  Market: '#00B4D8',
  Experiment: '#D946EF',
  Content: '#D946EF',
  Affiliate: '#D946EF',
  Sales: '#D946EF',
  Finance: '#FFD700',
  RiskManager: '#FF3B5C',
  Learning: '#00D26A',
  Factory: '#F5A623',
  DigitalProduct: '#FFD700',
}

export const DOMAIN_HEX: Record<DomainKey, string> = {
  exec: '#8B5CF6',
  research: '#00B4D8',
  market: '#00B4D8',
  content: '#D946EF',
  treasury: '#FFD700',
  risk: '#FF3B5C',
  learning: '#00D26A',
  protocol: '#D946EF',
  fabrication: '#F5A623',
  product: '#FFD700',
}

export const ACTIVITY_COLOR: Record<string, string> = {
  transaction: '#00D26A',
  risk: '#FF3B5C',
  decision: '#8B5CF6',
  learning: '#00B4D8',
}