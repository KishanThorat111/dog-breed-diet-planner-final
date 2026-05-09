'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function SignInPage() {
  const router = useRouter();
  
  useEffect(() => {
    router.push('/analyze');
  }, [router]);

  return null;
}
