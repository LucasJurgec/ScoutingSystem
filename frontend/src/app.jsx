import { BrowserRouter, Routes, Route } from 'react-router-dom';
import StatPage from './components/StatPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<p>Home page coming soon. Go to /player/&lt;id&gt;</p>} />
        <Route path="/player/:playerId" element={<StatPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;