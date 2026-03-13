import { createContext, useCallback, useContext, useState } from "react";
import ConfirmModal from "@/components/ConfirmModal";
import AlertModal from "@/components/AlertModal";

export interface ConfirmOptions {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "primary";
  onConfirm: () => void | Promise<void>;
}

export interface AlertOptions {
  title?: string;
  message: string;
}

interface ModalContextValue {
  showConfirm: (options: ConfirmOptions) => void;
  showAlert: (options: AlertOptions) => void;
}

const ModalContext = createContext<ModalContextValue | null>(null);

export function ModalProvider({ children }: { children: React.ReactNode }) {
  const [confirmState, setConfirmState] = useState<{
    open: boolean;
    title: string;
    message: string;
    confirmLabel?: string;
    cancelLabel?: string;
    variant?: "danger" | "primary";
    onConfirm: () => void | Promise<void>;
  }>({
    open: false,
    title: "",
    message: "",
    onConfirm: () => {},
  });
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [alertState, setAlertState] = useState<{
    open: boolean;
    title?: string;
    message: string;
  }>({ open: false, message: "" });

  const showConfirm = useCallback((options: ConfirmOptions) => {
    setConfirmState({
      open: true,
      title: options.title,
      message: options.message,
      confirmLabel: options.confirmLabel,
      cancelLabel: options.cancelLabel,
      variant: options.variant,
      onConfirm: options.onConfirm,
    });
  }, []);

  const showAlert = useCallback((options: AlertOptions) => {
    setAlertState({
      open: true,
      title: options.title,
      message: options.message,
    });
  }, []);

  const handleConfirmConfirm = useCallback(async () => {
    setConfirmLoading(true);
    try {
      await confirmState.onConfirm();
      setConfirmState((s) => ({ ...s, open: false }));
    } catch (_e) {
      // Caller can show error via showAlert; keep modal open so user can cancel or retry
    } finally {
      setConfirmLoading(false);
    }
  }, [confirmState.onConfirm]);

  const handleConfirmCancel = useCallback(() => {
    setConfirmState((s) => ({ ...s, open: false }));
  }, []);

  const handleAlertClose = useCallback(() => {
    setAlertState({ open: false, message: "" });
  }, []);

  return (
    <ModalContext.Provider value={{ showConfirm, showAlert }}>
      {children}
      <ConfirmModal
        open={confirmState.open}
        title={confirmState.title}
        message={confirmState.message}
        confirmLabel={confirmState.confirmLabel}
        cancelLabel={confirmState.cancelLabel}
        variant={confirmState.variant}
        onConfirm={handleConfirmConfirm}
        onCancel={handleConfirmCancel}
        loading={confirmLoading}
      />
      <AlertModal
        open={alertState.open}
        title={alertState.title}
        message={alertState.message}
        onClose={handleAlertClose}
      />
    </ModalContext.Provider>
  );
}

export function useModal() {
  const ctx = useContext(ModalContext);
  if (!ctx) throw new Error("useModal must be used within ModalProvider");
  return ctx;
}
