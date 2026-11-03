export type Role = 'duke' | 'assassin' | 'captain' | 'ambassador' | 'contessa'
export type ActionId =
  | 'income'
  | 'foreign_aid'
  | 'coup'
  | 'tax'
  | 'assassinate'
  | 'exchange'
  | 'steal'

export interface AgentOption {
  id: string
  name: string
}

export interface InfluenceCard {
  role: Role | null
  revealed: boolean
}

export interface PlayerState {
  id: string
  name: string
  kind: 'human' | 'agent'
  agentId?: string
  coins: number
  influence: number
  cards: InfluenceCard[]
}

export interface GameState {
  players: PlayerState[]
  currentPlayerIndex: number
  turn: number
  winnerId: string | null
  availableActions: ActionId[]
  log: string[]
}

interface ChallengePrompt {
  id: string
  type: 'challenge'
  decisionPlayerId: string
  claimantId: string
  role: Role
  action: ActionId | null
}

interface BlockPrompt {
  id: string
  type: 'block'
  decisionPlayerId: string
  actorId: string
  targetId: string | null
  action: 'foreign_aid' | 'assassinate' | 'steal'
  roles: Role[]
}

interface InfluencePrompt {
  id: string
  type: 'influence'
  playerId: string
  cards: { index: number; role: Role }[]
}

interface ExchangePrompt {
  id: string
  type: 'exchange'
  playerId: string
  cards: { index: number; role: Role }[]
  keepCount: number
}

export type DecisionPrompt =
  | ChallengePrompt
  | BlockPrompt
  | InfluencePrompt
  | ExchangePrompt

export type PlayerDecision =
  | boolean
  | { block: boolean; role?: Role }
  | number
  | number[]

export interface ServerState {
  game: GameState | null
  prompt: DecisionPrompt | null
  busy: boolean
  error: string | null
}

const ROLE_NAMES: Record<Role, string> = {
  duke: 'Duke',
  assassin: 'Assassin',
  captain: 'Captain',
  ambassador: 'Ambassador',
  contessa: 'Contessa',
}

const ACTION_NAMES: Record<ActionId, string> = {
  income: 'Income',
  foreign_aid: 'Foreign Aid',
  coup: 'Coup',
  tax: 'Tax',
  assassinate: 'Assassination',
  exchange: 'Exchange',
  steal: 'Steal',
}

export function roleName(role: Role): string {
  return ROLE_NAMES[role]
}

export function actionName(action: ActionId): string {
  return ACTION_NAMES[action]
}

export function alive(player: PlayerState): boolean {
  return player.influence > 0
}
