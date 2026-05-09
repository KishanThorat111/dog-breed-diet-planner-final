'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function SignUpPage() {
  const router = useRouter();
  
  useEffect(() => {
    router.push('/dashboard/analyze');
  }, [router]);

  return null;
}
