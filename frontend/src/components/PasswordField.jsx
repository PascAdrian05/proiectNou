import { useId, useState } from "react";

export function PasswordField({ label, placeholder, value, onChange, minLength, maxLength, required }) {
  const [isVisible, setIsVisible] = useState(false);
  const inputId = useId();

  return (
    <label htmlFor={inputId}>
      {label}
      <div className="password-field">
        <input
          id={inputId}
          type={isVisible ? "text" : "password"}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          minLength={minLength}
          maxLength={maxLength}
          required={required}
        />
        <button type="button" className="password-toggle" onClick={() => setIsVisible((current) => !current)}>
          {isVisible ? "Hide" : "Show"}
        </button>
      </div>
    </label>
  );
}
