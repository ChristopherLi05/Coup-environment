import { useEffect, useRef, useState } from 'react'
import './App.css'
import {
  actionName,
  alive,
  roleName,
  type ActionId,
  type AgentOption,
  type DecisionPrompt,
  type GameState,
  type PlayerDecision,
  type Role,
  type ServerState,
} from './game'

const ACTIONS: {
  id: ActionId
  description: string
  claim?: Role
  cost?: number
  target?: boolean
}[] = [
  { id: 'income', description: 'Take 1 coin from the Treasury.' },
  { id: 'foreign_aid', description: 'Take 2 coins. The Duke can block this.' },
  { id: 'coup', description: 'Pay 7 coins. The target loses an influence.', cost: 7, target: true },
  { id: 'tax', description: 'Claim Duke to take 3 coins.', claim: 'duke' },
  { id: 'assassinate', description: 'Claim Assassin. Pay 3 coins to remove influence.', claim: 'assassin', cost: 3, target: true },
  { id: 'exchange', description: 'Claim Ambassador to exchange Court cards.', claim: 'ambassador' },
  { id: 'steal', description: 'Claim Captain to take up to 2 coins.', claim: 'captain', target: true },
]

const ROLE_SHORT: Record<Role, string> = {
  duke: 'DU',
  assassin: 'AS',
  captain: 'CA',
  ambassador: 'AM',
  contessa: 'CO',
}

function coinLabel(amount: number): string {
  return `${amount} ${amount === 1 ? 'coin' : 'coins'}`
}

function App() {
  const [agentCount, setAgentCount] = useState(3)
  const [agents, setAgents] = useState<AgentOption[]>([])
  const [selectedAgents, setSelectedAgents] = useState<string[]>([
    'HonestRandom',
    'AlwaysDuke',
    'RandomAgent',
    'PassiveAgent',
    'HonestRandom',
  ])
  const [isSetup, setIsSetup] = useState(true)
  const [isBusy, setIsBusy] = useState(false)
  const [selectedAction, setSelectedAction] = useState<ActionId | null>(null)
  const [prompt, setPrompt] = useState<DecisionPrompt | null>(null)
  const [selectedCards, setSelectedCards] = useState<number[]>([])
  const [notice, setNotice] = useState('')
  const [apiError, setApiError] = useState('')
  const [game, setGame] = useState<GameState | null>(null)
  const promptRef = useRef<string | null>(null)

  useEffect(() => {
    let active = true
    void fetch('/api/agents')
      .then(async (response) => {
        if (!response.ok) throw new Error(`Agent list request failed (${response.status}).`)
        return response.json() as Promise<AgentOption[]>
      })
      .then((availableAgents) => {
        if (!active) return
        setAgents(availableAgents)
        if (availableAgents.length) {
          setSelectedAgents((selected) => selected.map((id, index) =>
            availableAgents.some((agent) => agent.id === id)
              ? id
              : availableAgents[index % availableAgents.length].id,
          ))
        }
        setApiError('')
      })
      .catch((error: unknown) => {
        if (active) {
          setApiError(error instanceof Error ? error.message : 'Could not reach the Coup API.')
        }
      })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (isSetup) return
    let active = true
    const pollState = async () => {
      try {
        const response = await fetch('/api/game')
        if (!response.ok) throw new Error(`Game state request failed (${response.status}).`)
        const serverState = await response.json() as ServerState
        if (!active) return
        setGame(serverState.game)
        setIsBusy(serverState.busy)
        setNotice(serverState.error ?? '')
        if (serverState.prompt?.id !== promptRef.current) {
          promptRef.current = serverState.prompt?.id ?? null
          setPrompt(serverState.prompt)
          setSelectedCards([])
        }
        setApiError('')
      } catch (error) {
        if (active) {
          setApiError(error instanceof Error ? error.message : 'Could not reach the Coup API.')
        }
      }
    }
    void pollState()
    const timer = window.setInterval(() => { void pollState() }, 300)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [isSetup])

  const startGame = async () => {
    setNotice('')
    try {
      const response = await fetch('/api/game', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agents: selectedAgents.slice(0, agentCount) }),
      })
      const result = await response.json() as { game?: GameState; error?: string }
      if (!response.ok) throw new Error(result.error ?? `Game setup failed (${response.status}).`)
      setGame(result.game ?? null)
      setIsBusy(false)
      setPrompt(null)
      promptRef.current = null
      setSelectedAction(null)
      setIsSetup(false)
      setApiError('')
    } catch (error) {
      setApiError(error instanceof Error ? error.message : 'Could not start a game.')
    }
  }

  const runTurn = async (action: ActionId, targetId: string | null) => {
    setIsBusy(true)
    setSelectedAction(null)
    setNotice('')
    try {
      const response = await fetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, targetId }),
      })
      const result = await response.json() as { error?: string }
      if (!response.ok) throw new Error(result.error ?? `Action failed (${response.status}).`)
    } catch (error) {
      setIsBusy(false)
      setNotice(error instanceof Error ? error.message : 'The turn could not be completed.')
    }
  }

  const submitDecision = async (decision: PlayerDecision) => {
    if (!prompt) return
    const promptId = prompt.id
    setPrompt(null)
    setIsBusy(true)
    try {
      const response = await fetch('/api/decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ promptId, decision }),
      })
      const result = await response.json() as { error?: string }
      if (!response.ok) throw new Error(result.error ?? `Decision failed (${response.status}).`)
    } catch (error) {
      promptRef.current = null
      setNotice(error instanceof Error ? error.message : 'Could not submit that decision.')
    }
  }

  const currentPlayer = game?.players[game.currentPlayerIndex]
  const human = game?.players.find((player) => player.kind === 'human')
  const isHumanTurn = currentPlayer?.kind === 'human' && !isBusy && !game?.winnerId
  const availableActions = game?.availableActions ?? []
  const actionDetails = selectedAction
    ? ACTIONS.find((action) => action.id === selectedAction)
    : null
  const targets = game?.players.filter(
    (player) => player.id !== currentPlayer?.id && alive(player),
  ) ?? []

  const changeAgent = (index: number, agentId: string) => {
    setSelectedAgents((current) => current.map((item, position) => position === index ? agentId : item))
  }

  const chooseAction = (action: ActionId) => {
    setSelectedAction(action)
    if (!ACTIONS.find((item) => item.id === action)?.target) {
      void runTurn(action, null)
    }
  }

  const chooseTarget = (playerId: string) => {
    if (currentPlayer && selectedAction) {
      void runTurn(selectedAction, playerId)
    }
  }

  const selectedPromptCards =
    prompt?.type === 'influence' || prompt?.type === 'exchange' ? prompt.cards : []
  const requiredCards = prompt?.type === 'exchange' ? prompt.keepCount : 1
  const toggleCard = (index: number) => {
    setSelectedCards((cards) => {
      if (cards.includes(index)) return cards.filter((card) => card !== index)
      if (cards.length >= requiredCards) return [...cards.slice(1), index]
      return [...cards, index]
    })
  }

  const renderPrompt = () => {
    if (!prompt || !game) return null
    const decisionPlayer =
      prompt.type === 'challenge' || prompt.type === 'block'
        ? game.players.find((player) => player.id === prompt.decisionPlayerId)
        : game.players.find((player) => player.id === prompt.playerId)
    if (!decisionPlayer || decisionPlayer.kind !== 'human') return null

    return (
      <div className="dialog-scrim">
        <section className="decision-dialog" role="dialog" aria-modal="true">
          <div className="dialog-kicker">YOUR DECISION</div>
          {prompt.type === 'challenge' && (
            <>
              <span className="dialog-emblem role-emblem" data-role={prompt.role}>
                {ROLE_SHORT[prompt.role]}
              </span>
              <h2>Challenge the claim?</h2>
              <p>
                <strong>{game.players.find((player) => player.id === prompt.claimantId)?.name}</strong>
                {' '}claims {roleName(prompt.role)}
                {prompt.action ? ` for ${actionName(prompt.action)}` : ''}.
                If they prove it, you lose an influence.
              </p>
              <div className="dialog-actions">
                <button className="button button-quiet" onClick={() => submitDecision(false)}>
                  Let it stand
                </button>
                <button className="button button-danger" onClick={() => submitDecision(true)}>
                  Challenge claim
                </button>
              </div>
            </>
          )}
          {prompt.type === 'block' && (
            <>
              <span className="dialog-emblem">!</span>
              <h2>Counter their action?</h2>
              <p>
                {game.players.find((player) => player.id === prompt.actorId)?.name}
                {' '}attempts {actionName(prompt.action)}. You can block by claiming
                {' '}{prompt.roles.map(roleName).join(' or ')}.
              </p>
              <div className="dialog-actions">
                <button className="button button-quiet" onClick={() => submitDecision({ block: false })}>
                  Let it happen
                </button>
                {prompt.roles.map((role) => (
                  <button
                    className="button button-primary"
                    key={role}
                    onClick={() => submitDecision({ block: true, role })}
                  >
                    Block with {roleName(role)}
                  </button>
                ))}
              </div>
            </>
          )}
          {(prompt.type === 'influence' || prompt.type === 'exchange') && (
            <>
              <span className="dialog-emblem">{prompt.type === 'exchange' ? '↔' : '✦'}</span>
              <h2>{prompt.type === 'exchange' ? 'Choose your influence' : 'Choose an influence to lose'}</h2>
              <p>
                {prompt.type === 'exchange'
                  ? `Keep ${prompt.keepCount} card${prompt.keepCount === 1 ? '' : 's'} in your hand. The rest return to the Court.`
                  : 'Choose one face-down card to reveal.'}
              </p>
              <div className="choice-cards">
                {selectedPromptCards.map((card) => {
                  const selected = selectedCards.includes(card.index)
                  return (
                    <button
                      className={`influence-card ${selected ? 'is-selected' : ''}`}
                      key={card.index}
                      onClick={() => toggleCard(card.index)}
                      aria-pressed={selected}
                    >
                      <span className="card-topline">{selected ? 'SELECTED' : roleName(card.role)}</span>
                      <span className="role-emblem" data-role={card.role}>{ROLE_SHORT[card.role]}</span>
                      <span className="card-role">{roleName(card.role)}</span>
                    </button>
                  )
                })}
              </div>
              <button
                className="button button-primary dialog-confirm"
                disabled={selectedCards.length !== requiredCards}
                onClick={() => submitDecision(
                  prompt.type === 'exchange' ? selectedCards : selectedCards[0],
                )}
              >
                {prompt.type === 'exchange' ? 'Keep selected cards' : 'Reveal this card'}
              </button>
            </>
          )}
        </section>
      </div>
    )
  }

  if (isSetup || !game) {
    return (
      <main className="setup-shell">
        <div className="setup-brand"><span className="brand-mark">C</span><span>THE COURT</span></div>
        <section className="setup-card">
          <div className="eyebrow">A GAME OF INFLUENCE</div>
          <h1>Coup: The Game</h1>
          <p className="setup-intro">
            Gather your influence, build your fortune, and outwit the court.
            The last player standing takes the throne.
          </p>
          <div className="setup-divider" />
          <div className="setup-section-head">
            <div>
              <div className="setup-label">YOUR TABLE</div>
              <p>Choose your opponents</p>
            </div>
            <div className="seat-stepper">
              <button
                aria-label="Remove one opponent"
                disabled={agentCount <= 1}
                onClick={() => setAgentCount((count) => Math.max(1, count - 1))}
              >−</button>
              <span>{agentCount + 1}<small> seats</small></span>
              <button
                aria-label="Add one opponent"
                disabled={agentCount >= 5}
                onClick={() => setAgentCount((count) => Math.min(5, count + 1))}
              >+</button>
            </div>
          </div>
          <div className="opponent-list">
            {selectedAgents.slice(0, agentCount).map((agentId, index) => (
              <label className="opponent-row" key={`opponent-${index}`}>
                <span className="opponent-avatar">{index + 1}</span>
                <span className="opponent-caption">OPPONENT {String(index + 1).padStart(2, '0')}</span>
                <select
                  aria-label={`Opponent ${index + 1} agent`}
                  value={agentId}
                  onChange={(event) => changeAgent(index, event.target.value)}
                >
                  {agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}
                </select>
              </label>
            ))}
          </div>
          {apiError && <div className="notice" role="alert">{apiError}. Start the Python API with <code>python server.py</code> from the app folder.</div>}
          <button className="button button-primary start-button" disabled={!agents.length} onClick={() => void startGame()}>
            Start a new game <span aria-hidden="true">→</span>
          </button>
          <div className="setup-footnote">2–6 PLAYERS <span /> 15 INFLUENCE CARDS <span /> ONE WINNER</div>
        </section>
        <footer className="setup-footer">A little influence goes a long way.</footer>
      </main>
    )
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="wordmark" href="#" onClick={(event) => event.preventDefault()}>
          <span className="brand-mark">C</span>
          <span className="wordmark-text">THE COURT<small>COUP · THE CARD GAME</small></span>
        </a>
        <div className="topbar-center"><span className="live-dot" /> GAME IN PROGRESS <span className="topbar-separator">/</span> TURN {game.turn}</div>
        <button className="new-game-button" disabled={isBusy} onClick={() => setIsSetup(true)}>New game <span>↗</span></button>
      </header>

      <main className="game-layout">
        <section className="table-column">
          <div className="table-heading">
            <div>
              <div className="eyebrow">THE CITADEL · ROUND {game.turn}</div>
              <h1>{game.winnerId ? 'The court has a ruler.' : currentPlayer?.kind === 'human' ? 'Your move.' : `${currentPlayer?.name} is thinking.`}</h1>
              <p>{game.winnerId ? `${game.players.find((player) => player.id === game.winnerId)?.name} claims the throne.` : currentPlayer?.kind === 'human' ? 'Choose one action. Make it count.' : 'Watch closely. Every claim leaves a trail.'}</p>
            </div>
            <div className="table-counter"><span>{game.players.filter(alive).length}</span><small>PLAYERS<br />REMAIN</small></div>
          </div>

          <div className="game-table">
            <div className="table-grid">
              {game.players.map((player) => (
                <article
                  className={`player-seat ${player.id === currentPlayer?.id ? 'is-current' : ''} ${!alive(player) ? 'is-eliminated' : ''} ${player.kind === 'human' ? 'is-human' : ''}`}
                  key={player.id}
                >
                  <div className="seat-header">
                    <span className="seat-avatar">{player.kind === 'human' ? 'Y' : player.name.charAt(0)}</span>
                    <div className="seat-name">{player.name}<small>{!alive(player) ? 'ELIMINATED' : player.id === currentPlayer?.id ? 'ON THE MOVE' : player.kind === 'human' ? 'YOU' : player.agentId?.replace(/([a-z])([A-Z])/g, '$1 $2').toUpperCase()}</small></div>
                    <div className="seat-coins"><span className="coin-icon">¢</span>{player.coins}</div>
                  </div>
                  <div className="seat-influence">
                    {player.cards.map((card, cardIndex) => (
                      <div
                        className={`mini-card ${card.revealed ? 'is-revealed' : 'is-hidden'} ${player.kind === 'human' && !card.revealed ? 'is-own' : ''}`}
                        key={`${player.id}-${cardIndex}`}
                        title={card.revealed || player.kind === 'human' ? card.role ? roleName(card.role) : 'Unknown influence' : 'Hidden influence'}
                      >
                        {card.revealed || player.kind === 'human'
                          ? card.role && <span className="role-emblem" data-role={card.role}>{ROLE_SHORT[card.role]}</span>
                          : <span className="card-back-mark">✦</span>}
                      </div>
                    ))}
                    <span className="influence-count">{player.influence} influence</span>
                  </div>
                </article>
              ))}
              <div className="table-center">
                <div className="court-seal"><span>THE<br />COURT</span><i>✦</i></div>
                <div className="court-caption">THE COMMON COURT</div>
                <div className="treasury"><span className="coin-icon">¢</span><span>TREASURY</span><strong>∞</strong></div>
              </div>
            </div>
          </div>

          <section className="action-panel">
            <div className="panel-title-row">
              <div><div className="setup-label">{isHumanTurn ? 'YOUR TURN' : game.winnerId ? 'GAME COMPLETE' : 'ACTION'}</div><h2>{isHumanTurn ? 'Choose your action' : game.winnerId ? 'Well played.' : isBusy ? 'The court is responding…' : 'Waiting for the next turn'}</h2></div>
              {human && <div className="your-purse"><span className="coin-icon">¢</span><strong>{human.coins}</strong><span>YOUR COINS</span></div>}
            </div>

            {isHumanTurn && !selectedAction && (
              <div className="actions-grid">
                {ACTIONS.map((action) => {
                  const disabled = !availableActions.includes(action.id) ||
                    (action.cost !== undefined && (currentPlayer?.coins ?? 0) < action.cost)
                  return (
                    <button
                      className={`action-card ${disabled ? 'is-disabled' : ''}`}
                      disabled={disabled}
                      key={action.id}
                      onClick={() => chooseAction(action.id)}
                    >
                      <span className={`action-icon icon-${action.id}`}>{action.claim ? ROLE_SHORT[action.claim] : action.id === 'income' || action.id === 'foreign_aid' ? '¢' : '×'}</span>
                      <span className="action-copy"><strong>{actionName(action.id)}</strong><small>{action.description}</small></span>
                      {action.claim && <span className="claim-tag">{roleName(action.claim)} claim</span>}
                      {action.cost !== undefined && <span className="cost-tag">{action.cost}¢</span>}
                      {action.target && <span className="target-tag">TARGET</span>}
                    </button>
                  )
                })}
              </div>
            )}

            {isHumanTurn && selectedAction && actionDetails?.target && (
              <div className="target-picker">
                <div className="target-heading">
                  <strong>Choose your target</strong>
                  <button className="text-button" onClick={() => setSelectedAction(null)}>Cancel</button>
                </div>
                <div className="target-list">
                  {targets.map((target) => (
                    <button className="target-option" key={target.id} onClick={() => chooseTarget(target.id)}>
                      <span className="target-avatar">{target.name.charAt(0)}</span>
                      <span>{target.name}<small>{target.influence} influence · {coinLabel(target.coins)}</small></span>
                      <span className="target-arrow">→</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {isBusy && <div className="turn-status"><span className="loading-orb" /> Resolving claims, challenges, and counteractions…</div>}
            {game.winnerId && (
              <button className="button button-primary replay-button" onClick={() => setIsSetup(true)}>Play again <span>→</span></button>
            )}
            {notice && <div className="notice" role="alert">{notice}</div>}
          </section>
        </section>

        <aside className="right-rail">
          <section className="hand-panel">
            <div className="rail-heading">
              <div><div className="setup-label">YOUR INFLUENCE</div><h2>Your hand</h2></div>
              <span className="hand-count">{human?.cards.filter((card) => !card.revealed).length ?? 0} / 2</span>
            </div>
            <div className="hand-cards">
              {human?.cards.map((card, index) => (
                <div className={`hand-card ${card.revealed ? 'is-revealed' : ''}`} key={`hand-${index}`}>
                  <span className="hand-card-index">0{index + 1}</span>
                  {card.role
                    ? <><span className="role-emblem" data-role={card.role}>{ROLE_SHORT[card.role]}</span><strong>{roleName(card.role)}</strong><small>{card.revealed ? 'REVEALED' : 'FACE DOWN'}</small></>
                    : <><span className="card-back-mark">✦</span><strong>Hidden</strong><small>FACE DOWN</small></>}
                </div>
              ))}
            </div>
            <p className="private-note"><span>◉</span> Only you can see your face-down cards.</p>
          </section>

          <section className="log-panel">
            <div className="rail-heading">
              <div><div className="setup-label">WHAT'S HAPPENING</div><h2>Game log</h2></div>
              <span className="log-count">{game.log.length.toString().padStart(2, '0')}</span>
            </div>
            <ol className="event-list">
              {[...game.log].reverse().map((entry, index) => (
                <li className={index === 0 ? 'is-latest' : ''} key={`${game.log.length - index}-${entry}`}>
                  <span className="event-dot" />
                  <span>{entry}</span>
                </li>
              ))}
            </ol>
          </section>

          <div className="rules-note">
            <span className="rules-star">✦</span>
            <div><strong>Remember</strong><p>At 10 coins, a Coup is no longer a choice.</p></div>
          </div>
        </aside>
      </main>
      {renderPrompt()}
    </div>
  )
}

export default App
