'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { toast } from 'sonner';
import logo from '@/assets/logo.png';
import Link from 'next/link';

export default function SignupPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    name: '',
    organizationName: '',
    inviteCode: '',
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (formData.password !== formData.confirmPassword) {
      toast.error('Password Mismatch', {
        description: 'Please make sure both passwords match',
      });
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Registration failed');
      }

      toast.success('Registration successful', {
        description: 'Please sign in with your credentials',
      });
      router.push('/login');
    } catch (error) {
      toast.error('Registration failed', {
        description: error instanceof Error ? error.message : 'Please try again',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  return (
    <div className="flex min-h-screen w-screen items-center justify-center bg-gradient-to-b from-gray-50 to-gray-100">
      <Card className="w-[400px] shadow-lg">
        <CardContent>
          <div className="flex justify-center">
            <img src={logo.src} alt="OpenManus Logo" className="h-24 w-auto" />
          </div>
          <div className="mb-6">
            <CardDescription className="text-center text-base">Create your OpenManus account</CardDescription>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Input
                name="email"
                type="email"
                placeholder="Email"
                value={formData.email}
                onChange={handleChange}
                required
                disabled={isLoading}
                className="h-11"
              />
            </div>
            <div>
              <Input
                name="password"
                type="password"
                placeholder="Password"
                value={formData.password}
                onChange={handleChange}
                required
                disabled={isLoading}
                className="h-11"
              />
            </div>
            <div>
              <Input
                name="confirmPassword"
                type="password"
                placeholder="Confirm Password"
                value={formData.confirmPassword}
                onChange={handleChange}
                required
                disabled={isLoading}
                className="h-11"
              />
            </div>
            <div>
              <Input
                name="name"
                type="text"
                placeholder="Name"
                value={formData.name}
                onChange={handleChange}
                required
                disabled={isLoading}
                className="h-11"
              />
            </div>
            <div>
              <Input
                name="organizationName"
                type="text"
                placeholder="Organization Name"
                value={formData.organizationName}
                onChange={handleChange}
                required
                disabled={isLoading}
                className="h-11"
              />
            </div>
            <div>
              <Input
                name="inviteCode"
                type="text"
                placeholder="Invite Code"
                value={formData.inviteCode}
                onChange={handleChange}
                required
                disabled={isLoading}
                className="h-11"
              />
            </div>
            <Button type="submit" className="h-11 w-full text-base font-medium" disabled={isLoading}>
              {isLoading ? 'Creating Account...' : 'Create Account'}
            </Button>
            <div className="text-muted-foreground text-center text-sm">
              Already have an account?{' '}
              <Link href="/login" className="text-primary hover:underline">
                Sign in
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
