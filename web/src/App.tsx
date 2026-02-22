import { Routes, Route } from 'react-router-dom'
import { EntityProvider } from './context/EntityContext'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Wallets from './pages/Wallets'
import Transactions from './pages/Transactions'
import ParserDebug from './pages/ParserDebug'
import Journal from './pages/Journal'
import Accounts from './pages/Accounts'
import Errors from './pages/Errors'
import Tax from './pages/Tax'
import Reports from './pages/Reports'
import Entities from './pages/Entities'
import Imports from './pages/Imports'
import Analytics from './pages/Analytics'
import TaxAnalytics from './pages/TaxAnalytics'

export default function App() {
  return (
    <EntityProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/wallets" element={<Wallets />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/parser" element={<ParserDebug />} />
          <Route path="/journal" element={<Journal />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/errors" element={<Errors />} />
          <Route path="/tax" element={<Tax />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/entities" element={<Entities />} />
          <Route path="/imports" element={<Imports />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/tax/analytics" element={<TaxAnalytics />} />
        </Route>
      </Routes>
    </EntityProvider>
  )
}
