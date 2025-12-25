import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import './FamilyTree.css'

// Icons
const ChevronDownIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <path d="M6 9l6 6 6-6"/>
  </svg>
)

const ChevronUpIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <path d="M18 15l-6-6-6 6"/>
  </svg>
)

const HeartIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" stroke="none">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
  </svg>
)

const ExpandIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>
  </svg>
)

const CollapseIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M4 14h6v6M14 10h6V4M20 14l-6-6M4 10l6 6"/>
  </svg>
)

function TreeNode({ node, direction = 'none', onExpand, expandedNodes, depth = 0 }) {
  const isExpanded = expandedNodes.has(node.id)
  const hasParents = node.parents && node.parents.length > 0
  const hasChildren = node.children && node.children.length > 0
  const hasSpouses = node.spouses && node.spouses.length > 0

  const canExpand = (direction === 'up' && hasParents) ||
                    (direction === 'down' && hasChildren) ||
                    direction === 'none'

  const formatLifespan = (birthYear, deathYear) => {
    if (birthYear && deathYear) return `${birthYear} - ${deathYear}`
    if (birthYear) return `b. ${birthYear}`
    if (deathYear) return `d. ${deathYear}`
    return ''
  }

  const lifespan = formatLifespan(node.birthYear, node.deathYear)

  return (
    <div className={`tree-node-wrapper direction-${direction} depth-${depth}`}>
      {/* Parents (ancestors) - shown above */}
      {direction === 'up' && hasParents && isExpanded && (
        <div className="tree-branch ancestors-branch">
          <svg className="branch-connector ancestor-connector" preserveAspectRatio="none">
            <path className="connector-line" />
          </svg>
          <div className="tree-nodes-row">
            {node.parents.map((parent) => (
              <TreeNode
                key={parent.id}
                node={parent}
                direction="up"
                onExpand={onExpand}
                expandedNodes={expandedNodes}
                depth={depth + 1}
              />
            ))}
          </div>
        </div>
      )}

      {/* Current node with spouse(s) */}
      <div className="tree-node-group">
        <div
          className={`tree-node ${canExpand ? 'expandable' : ''} ${isExpanded ? 'expanded' : ''}`}
          onClick={() => canExpand && onExpand(node.id)}
          role={canExpand ? 'button' : undefined}
          tabIndex={canExpand ? 0 : undefined}
          onKeyDown={(e) => {
            if (canExpand && (e.key === 'Enter' || e.key === ' ')) {
              e.preventDefault()
              onExpand(node.id)
            }
          }}
        >
          <Link
            to={`/person/${node.id}`}
            className="node-link"
            onClick={(e) => e.stopPropagation()}
          >
            <span className="node-name">{node.displayName}</span>
          </Link>
          {lifespan && <span className="node-dates">{lifespan}</span>}

          {canExpand && (
            <span className="expand-toggle">
              {direction === 'up' ? (
                isExpanded ? <ChevronDownIcon /> : <ChevronUpIcon />
              ) : (
                isExpanded ? <ChevronUpIcon /> : <ChevronDownIcon />
              )}
            </span>
          )}
        </div>

        {/* Spouses */}
        {hasSpouses && (
          <div className="spouse-group">
            {node.spouses.map((spouse) => (
              <div key={spouse.id} className="spouse-wrapper">
                <span className="spouse-connector">
                  <HeartIcon />
                </span>
                <div className="tree-node spouse-node">
                  <Link to={`/person/${spouse.id}`} className="node-link">
                    <span className="node-name">{spouse.displayName}</span>
                  </Link>
                  {formatLifespan(spouse.birthYear, spouse.deathYear) && (
                    <span className="node-dates">
                      {formatLifespan(spouse.birthYear, spouse.deathYear)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Children (descendants) - shown below */}
      {direction === 'down' && hasChildren && isExpanded && (
        <div className="tree-branch descendants-branch">
          <svg className="branch-connector descendant-connector" preserveAspectRatio="none">
            <path className="connector-line" />
          </svg>
          <div className="tree-nodes-row">
            {node.children.map((child) => (
              <TreeNode
                key={child.id}
                node={child}
                direction="down"
                onExpand={onExpand}
                expandedNodes={expandedNodes}
                depth={depth + 1}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function FamilyTree({ ancestors, descendants, person }) {
  const [expandedNodes, setExpandedNodes] = useState(() => new Set([person?.id]))

  const toggleExpand = (nodeId) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev)
      if (next.has(nodeId)) {
        next.delete(nodeId)
      } else {
        next.add(nodeId)
      }
      return next
    })
  }

  const allNodeIds = useMemo(() => {
    const ids = new Set()
    const collectIds = (node) => {
      if (!node) return
      ids.add(node.id)
      node.parents?.forEach(collectIds)
      node.children?.forEach(collectIds)
    }
    collectIds(ancestors)
    collectIds(descendants)
    return ids
  }, [ancestors, descendants])

  const expandAll = () => {
    setExpandedNodes(allNodeIds)
  }

  const collapseAll = () => {
    setExpandedNodes(new Set([person?.id]))
  }

  const isAllExpanded = expandedNodes.size >= allNodeIds.size

  if (!person) {
    return (
      <div className="tree-empty">
        <p>No tree data available</p>
      </div>
    )
  }

  const formatLifespan = (birthYear, deathYear) => {
    if (birthYear && deathYear) return `${birthYear} - ${deathYear}`
    if (birthYear) return `b. ${birthYear}`
    if (deathYear) return `d. ${deathYear}`
    return ''
  }

  return (
    <div className="family-tree">
      <div className="tree-controls">
        <button
          onClick={isAllExpanded ? collapseAll : expandAll}
          className="tree-control-btn"
        >
          {isAllExpanded ? <CollapseIcon /> : <ExpandIcon />}
          <span>{isAllExpanded ? 'Collapse All' : 'Expand All'}</span>
        </button>
      </div>

      <div className="tree-container">
        {/* Ancestors section */}
        {ancestors && ancestors.parents && ancestors.parents.length > 0 && (
          <section className="tree-section ancestors-section">
            <h3 className="section-label">Ancestors</h3>
            <div className="tree-nodes-row">
              {ancestors.parents.map((parent) => (
                <TreeNode
                  key={parent.id}
                  node={parent}
                  direction="up"
                  onExpand={toggleExpand}
                  expandedNodes={expandedNodes}
                />
              ))}
            </div>
            <div className="section-connector" />
          </section>
        )}

        {/* Center person */}
        <section className="tree-section center-section">
          <div className="center-person-wrapper">
            <div className="tree-node center-node">
              <Link to={`/person/${person.id}`} className="node-link">
                <span className="node-name">{person.displayName}</span>
              </Link>
              {formatLifespan(person.birthYear, person.deathYear) && (
                <span className="node-dates">
                  {formatLifespan(person.birthYear, person.deathYear)}
                </span>
              )}
            </div>

            {/* Center person's spouses */}
            {ancestors?.spouses && ancestors.spouses.length > 0 && (
              <div className="spouse-group center-spouse-group">
                {ancestors.spouses.map((spouse) => (
                  <div key={spouse.id} className="spouse-wrapper">
                    <span className="spouse-connector">
                      <HeartIcon />
                    </span>
                    <div className="tree-node spouse-node">
                      <Link to={`/person/${spouse.id}`} className="node-link">
                        <span className="node-name">{spouse.displayName}</span>
                      </Link>
                      {formatLifespan(spouse.birthYear, spouse.deathYear) && (
                        <span className="node-dates">
                          {formatLifespan(spouse.birthYear, spouse.deathYear)}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Descendants section */}
        {descendants && descendants.children && descendants.children.length > 0 && (
          <section className="tree-section descendants-section">
            <div className="section-connector" />
            <h3 className="section-label">Descendants</h3>
            <div className="tree-nodes-row">
              {descendants.children.map((child) => (
                <TreeNode
                  key={child.id}
                  node={child}
                  direction="down"
                  onExpand={toggleExpand}
                  expandedNodes={expandedNodes}
                />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

export default FamilyTree
