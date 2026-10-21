import { useEffect, useRef } from 'react';
import './StatPageComponents/InfoModal.css';

// Pop-up panel built on the native <dialog>, so Esc-to-close and
// keeping keyboard focus inside the pop-up come for free.
function InfoModal({ title, open, onClose, children }) {
    const ref = useRef(null);
    const onCloseRef = useRef(onClose);
    onCloseRef.current = onClose;

    useEffect(() => {
        const dialog = ref.current;
        if (!dialog) return;
        if (open && !dialog.open) dialog.showModal();
        if (!open && dialog.open) dialog.close();
    }, [open]);

    // fires on Esc as well as on our close button
    useEffect(() => {
        const dialog = ref.current;
        const handleClose = () => onCloseRef.current();
        dialog.addEventListener('close', handleClose);
        return () => dialog.removeEventListener('close', handleClose);
    }, []);

    return (
        <dialog
            ref={ref}
            className="info-modal"
            aria-labelledby="info-modal-title"
            // clicking the dark backdrop (outside the panel) closes it
            onClick={(e) => { if (e.target === ref.current) onClose(); }}
        >
            <div className="info-modal-inner">
                <div className="info-modal-header">
                    <h3 id="info-modal-title">{title}</h3>
                    <button className="info-modal-close" onClick={onClose} aria-label="Close">×</button>
                </div>
                {open && children}
            </div>
        </dialog>
    );
}

export default InfoModal;
