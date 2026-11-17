import { MissionDialogView } from "@/features/game/components/MissionDialogView";
import { useMissionDialog } from "@/features/game/hooks/use-mission-dialog";

export const MissionDialog = () => {
  const dialog = useMissionDialog();

  if (!dialog.isOpen) {
    return null;
  }

  return (
    <MissionDialogView
      mission={dialog.mission}
      typedText={dialog.typedText}
      heardText={dialog.heardText}
      isListening={dialog.isListening}
      isMicUnavailable={dialog.isMicUnavailable}
      canType={dialog.canType}
      onTypedChange={dialog.onTypedChange}
      onMicDown={dialog.onMicDown}
      onMicUp={dialog.onMicUp}
      onSubmitTyped={dialog.onSubmitTyped}
      onClose={dialog.onClose}
    />
  );
};
