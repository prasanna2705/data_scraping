import { useState } from 'react';

const defaults = {
  brand: 'Lenovo',
  ram_gb: 16,
  storage_gb: 512,
  processor: 'Intel Core i7',
  gpu: 'NVIDIA RTX 4050',
  screen_size: 15.6,
  rating: 4.2,
};

export default function SpecForm({ onSubmit, submitText = 'Submit', budget = false }) {
  const [values, setValues] = useState({
    ...defaults,
    ...(budget ? { budget: 80000 } : {}),
  });

  const fields = [
    ['brand', 'Brand', 'text'],
    ['ram_gb', 'RAM (GB)', 'number'],
    ['storage_gb', 'Storage (GB)', 'number'],
    ['processor', 'Processor', 'text'],
    ['gpu', 'GPU', 'text'],
    ['screen_size', 'Screen Size', 'number'],
    ['rating', 'Rating', 'number'],
    ...(budget ? [['budget', 'Budget (₹)', 'number']] : []),
  ];

  return (
    <form
      className="spec-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(values);
      }}
    >
      {fields.map(([key, label, type]) => (
        <label key={key}>
          {label}
          <input
            type={type}
            required={key !== 'brand' && key !== 'gpu'}
            min={type === 'number' ? 0 : undefined}
            max={key === 'rating' ? 5 : undefined}
            step={key === 'screen_size' || key === 'rating' ? '0.1' : type === 'number' ? '1' : undefined}
            value={values[key]}
            onChange={(event) =>
              setValues({
                ...values,
                [key]: type === 'number' ? Number(event.target.value) : event.target.value,
              })
            }
          />
        </label>
      ))}
      <button type="submit">{submitText}</button>
    </form>
  );
}
