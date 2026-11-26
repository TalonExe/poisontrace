import React from "react";

export function Icon({ name, size = 16 }) {
  const paths = {
    menu: (
      <>
        <path d="M4 7h16M4 12h16M4 17h16" />
      </>
    ),
    search: (
      <>
        <circle cx="11" cy="11" r="6" />
        <path d="m16 16 4 4" />
      </>
    ),
    arrow: (
      <>
        <path d="M5 12h13M13 6l6 6-6 6" />
      </>
    ),
    chevron: <path d="m6 9 6 6 6-6" />,
    close: <path d="m6 6 12 12M6 18 18 6" />,
    trash: (
      <>
        <path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v5M14 11v5" />
      </>
    ),
    settings: (
      <>
        <path d="m9.4 3-.6 2.5-2 .9-2.3-.9-2.1 3.6 1.8 1.7v2.4l-1.8 1.7 2.1 3.6 2.3-.9 2 .9.6 2.5h4.2l.6-2.5 2-.9 2.3.9 2.1-3.6-1.8-1.7v-2.4l1.8-1.7-2.1-3.6-2.3.9-2-.9-.6-2.5Z" transform="translate(.5)" />
        <circle cx="12" cy="12" r="3" />
      </>
    ),
    shield: (
      <>
        <path d="M12 3 19 6v5c0 4.6-3 8-7 10-4-2-7-5.4-7-10V6l7-3Z" />
        <path d="m9 12 2 2 4-4" />
      </>
    ),
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}

export function Select({ label, value, onChange, options, disabled = false }) {
  return (
    <label className="field">
      <span>{label}</span>
      <div className="select-wrap">
        <select
          disabled={disabled}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        >
          {options.map((option) => (
            <option key={option}>{option}</option>
          ))}
        </select>
        <Icon name="chevron" size={14} />
      </div>
    </label>
  );
}

export function CardHead({ label, title, pill, tone }) {
  return (
    <div className="card-head">
      <div>
        <h2>{title}</h2>
      </div>
      {pill && <span className={`pill ${tone}`}>{pill}</span>}
    </div>
  );
}
