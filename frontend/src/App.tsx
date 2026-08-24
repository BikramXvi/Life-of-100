import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/shell/Layout'
import City from './pages/City'
import People from './pages/People'
import Investigate from './pages/Investigate'
import Experiment from './pages/Experiment'
import Events from './pages/Events'
import CalendarPage from './pages/Calendar'
import Disasters from './pages/Disasters'
import AiAgents from './pages/AiAgents'
import Analytics from './pages/Analytics'
import Timelines from './pages/Timelines'
import Observability from './pages/Observability'
import Search from './pages/Search'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/city" replace />} />
        <Route path="/city" element={<City />} />
        <Route path="/experiment" element={<Experiment />} />
        <Route path="/investigate" element={<Investigate />} />
        <Route path="/people" element={<People />} />
        <Route path="/people/:citizenId" element={<People />} />
        <Route path="/events" element={<Events />} />
        <Route path="/calendar" element={<CalendarPage />} />
        <Route path="/disasters" element={<Disasters />} />
        <Route path="/ai-agents" element={<AiAgents />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/timelines" element={<Timelines />} />
        <Route path="/observability" element={<Observability />} />
        <Route path="/search" element={<Search />} />
        <Route path="*" element={<Navigate to="/city" replace />} />
      </Route>
    </Routes>
  )
}
