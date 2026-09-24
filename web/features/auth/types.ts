export interface User {
  id: number;
  email: string;
  has_usable_password: boolean;
  is_vendor: boolean;
}

export interface AuthResponse {
  access: string;
  user: User;
}

export interface RegisterPayload {
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}
