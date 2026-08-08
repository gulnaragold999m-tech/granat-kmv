'use client';

import { useState } from 'react';
import Link from 'next/link';

export default function FormWithConsent() {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name || !phone || !consent) {
      setError('Пожалуйста, заполните все поля и согласитесь с политикой');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, phone, email, consent }),
      });

      if (response.ok) {
        setSuccess(true);
        setName('');
        setPhone('');
        setEmail('');
        setConsent(false);
        setTimeout(() => setSuccess(false), 3000);
      } else {
        setError('Ошибка при отправке заявки. Попробуйте позже.');
      }
    } catch (err) {
      setError('Ошибка соединения. Попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <input
        type="text"
        placeholder="Ваше имя"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-600"
        required
      />

      <input
        type="tel"
        placeholder="Телефон"
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-600"
        required
      />

      <input
        type="email"
        placeholder="Email (опционально)"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-600"
      />

      <label className="flex items-start gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          className="mt-1 w-5 h-5"
          required
        />
        <span className="text-sm text-gray-600">
          Я согласен с{' '}
          <Link href="/privacy" className="text-red-600 hover:underline">
            политикой конфиденциальности
          </Link>
          {' '}и даю согласие на обработку персональных данных
        </span>
      </label>

      {error && <p className="text-red-600 text-sm">{error}</p>}
      {success && <p className="text-green-600 text-sm">Заявка отправлена! Мы свяжемся с вами в течение часа.</p>}

      <button
        type="submit"
        disabled={loading}
        className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition disabled:opacity-50"
      >
        {loading ? 'Отправка...' : 'Отправить заявку'}
      </button>
    </form>
  );
}
