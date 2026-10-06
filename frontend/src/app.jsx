import { BrowserRouter, Routes, Route } from 'react-router-dom';
import StatPage from './components/StatPage';
import SelectPage from './components/SelectPage';

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<SelectPage />} />
                <Route path="/player/:playerId" element={<StatPage />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
