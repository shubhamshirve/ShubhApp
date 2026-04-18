import { useState, useEffect } from "react";
import { useAuth } from "../App";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { Bell } from "lucide-react";

/**
 * WelcomeModal — shows an admin-configured announcement popup on first login.
 * Tracks per-user + per-version in localStorage so it only shows once per version.
 */
const WelcomeModal = () => {
  const { authAxios, user } = useAuth();
  const [open, setOpen] = useState(false);
  const [modal, setModal] = useState(null);

  useEffect(() => {
    if (!user) return;
    fetchAndMaybeShow();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const fetchAndMaybeShow = async () => {
    try {
      const res = await authAxios.get("/admin/welcome-modal");
      const data = res.data;

      if (!data.enabled || !data.content) return;

      // Check audience filter
      const showFor = data.show_for || "all";
      if (showFor === "operators" && user.role === "admin") return;
      if (showFor === "admins" && user.role !== "admin") return;

      // Check if user has already seen this version
      const storageKey = `${user.id}_welcome_v`;
      const seenVersion = parseInt(localStorage.getItem(storageKey) || "0");
      if (seenVersion >= data.version) return;

      setModal(data);
      setOpen(true);
    } catch {
      // silently fail — non-critical feature
    }
  };

  const handleClose = () => {
    if (modal && user) {
      localStorage.setItem(`${user.id}_welcome_v`, String(modal.version));
    }
    setOpen(false);
  };

  if (!modal) return null;

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) handleClose(); }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <Bell className="w-5 h-5 text-indigo-500" />
            {modal.title || "Welcome"}
          </DialogTitle>
        </DialogHeader>
        <div className="py-2">
          <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
            {modal.content}
          </p>
        </div>
        <div className="flex justify-end pt-2">
          <Button onClick={handleClose} className="bg-indigo-600 hover:bg-indigo-700 text-white">
            Got it
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default WelcomeModal;
