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

export function Select({ label, value, onChange, options }) {
  return (
    <label className="field">
      <span>{label}</span>
      <div className="select-wrap">
        <select
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
