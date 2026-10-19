import { useState } from 'react';
import { RouterProvider } from 'react-router-dom';
import { Providers } from './providers';
import { router } from './router';

export function App() {
  const [r] = useState(router);
  return (
    <Providers>
      <RouterProvider router={r} />
    </Providers>
  );
}
