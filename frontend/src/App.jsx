import { Routes, Route, Link } from 'react-router-dom'
import Home       from './Home'
import Wrestler   from './Wrestler'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/wrestler/:name" element={<Wrestler />} />
    </Routes>
  )
}

export default App
