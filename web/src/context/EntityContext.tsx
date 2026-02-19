import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

interface EntityContextValue {
  entityId: string | null
  setEntityId: (id: string | null) => void
}

const EntityContext = createContext<EntityContextValue>({
  entityId: null,
  setEntityId: () => {},
})

export function EntityProvider({ children }: { children: ReactNode }) {
  const [entityId, setEntityId] = useState<string | null>(() => {
    return localStorage.getItem('selectedEntityId')
  })

  useEffect(() => {
    if (entityId) {
      localStorage.setItem('selectedEntityId', entityId)
    } else {
      localStorage.removeItem('selectedEntityId')
    }
  }, [entityId])

  return (
    <EntityContext.Provider value={{ entityId, setEntityId }}>
      {children}
    </EntityContext.Provider>
  )
}

export function useEntity() {
  return useContext(EntityContext)
}
