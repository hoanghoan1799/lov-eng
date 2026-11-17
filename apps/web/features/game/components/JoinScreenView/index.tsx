import { type Gender,GENDERS } from "@park/shared";

import { GAME_TITLE, PROFILE_COLORS } from "@/features/game/constants/game";

export interface JoinScreenViewProps {
  name: string;
  birthYear: string;
  gender: Gender;
  top: string;
  hair: string;
  bottom: string;
  shoes: string;
  isUnderage: boolean;
  isYearInvalid: boolean;
  minAge: number;
  isConnecting: boolean;
  errorMessage: string | null;
  onNameChange: (value: string) => void;
  onBirthYearChange: (value: string) => void;
  onGenderChange: (value: Gender) => void;
  onTopChange: (value: string) => void;
  onHairChange: (value: string) => void;
  onBottomChange: (value: string) => void;
  onShoesChange: (value: string) => void;
  onSubmit: () => void;
}

interface SwatchesProps {
  label: string;
  colors: readonly string[];
  value: string;
  onChange: (value: string) => void;
}

const Swatches = ({ label, colors, value, onChange }: SwatchesProps) => (
  <div className="field">
    <span>{label}</span>
    <div className="swatches">
      {colors.map((color) => (
        <button
          key={color}
          type="button"
          aria-label={`${label} ${color}`}
          className={color === value ? "selected" : ""}
          style={{ background: color }}
          onClick={() => onChange(color)}
        />
      ))}
    </div>
  </div>
);

export const JoinScreenView = ({
  name,
  birthYear,
  gender,
  top,
  hair,
  bottom,
  shoes,
  isUnderage,
  isYearInvalid,
  minAge,
  isConnecting,
  errorMessage,
  onNameChange,
  onBirthYearChange,
  onGenderChange,
  onTopChange,
  onHairChange,
  onBottomChange,
  onShoesChange,
  onSubmit,
}: JoinScreenViewProps) => (
  <main className="join-screen">
    <form
      className="join-card"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <h1>{GAME_TITLE}</h1>
      <p className="tagline">Explore the island, meet people, and practise English by talking.</p>
      <label className="field">
        <span>Your name</span>
        <input value={name} maxLength={20} onChange={(event) => onNameChange(event.target.value)} placeholder="e.g. Linh" />
      </label>
      <label className="field">
        <span>Birth year (adults {minAge}+ only)</span>
        <input value={birthYear} inputMode="numeric" maxLength={4} onChange={(event) => onBirthYearChange(event.target.value.replace(/\D/g, ""))} placeholder="e.g. 1995" />
      </label>
      {isUnderage ? <p className="error">Sorry, this game is for adults aged {minAge} and over.</p> : null}
      {isYearInvalid ? <p className="error">Please enter a valid birth year.</p> : null}
      <div className="field">
        <span>Character</span>
        <div className="gender">
          {GENDERS.map((item) => (
            <button key={item} type="button" className={item === gender ? "selected" : ""} onClick={() => onGenderChange(item)}>
              {item === "boy" ? "Boy" : "Girl"}
            </button>
          ))}
        </div>
      </div>
      <Swatches label="Outfit" colors={PROFILE_COLORS.tops} value={top} onChange={onTopChange} />
      <Swatches label="Trousers / skirt" colors={PROFILE_COLORS.bottoms} value={bottom} onChange={onBottomChange} />
      <Swatches label="Shoes" colors={PROFILE_COLORS.shoes} value={shoes} onChange={onShoesChange} />
      <Swatches label="Hair" colors={PROFILE_COLORS.hairs} value={hair} onChange={onHairChange} />
      {errorMessage ? <p className="error">{errorMessage}</p> : null}
      <button type="submit" className="primary" disabled={isConnecting}>
        {isConnecting ? "Connecting…" : "Enter the island"}
      </button>
    </form>
  </main>
);
