"use client";

import Image from "next/image";
import trekyatra from "@/app/Images/ty.png";
import black from "@/app/Images/black.jpg";
import { Metadata } from "next";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Link from "next/link";
import "@/app/stylesheet/login.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faEye, faEyeSlash } from "@fortawesome/free-solid-svg-icons";

export const logMetadata: Metadata = {
  title: "Trekyatra- Login",
  description: "Login to Trekyatra",
};

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email || !password) {
      setError("Please fill in the both fields.");
    }

    try {
      const response = await fetch("http://127.0.0.1:5000/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        throw new Error("Invalid Credentials");
      }
      router.push("/");
    } catch (err) {
      setError("Invalid Credentials");
    }
  };

  return (
    <div className="trek-log-main">
      <div className="trek-log-img">
        <Image
          src={trekyatra}
          alt="Logo_TrekYatra"
          className="trek-log-image"
          priority
        />
      </div>

      <div className="trek-log">
        <div className="trek-log-left">
          <Image
            src={black}
            alt="Side_TrekYatra"
            className="trek-log-left-image"
            priority
          />
        </div>
        <div className="trek-log-right">
          <form onSubmit={handleLogin}>
            <div className="input">
              <label className="label" htmlFor="Email">
                Email
              </label>
              <div className="log-mail">
                <input
                  type="email"
                  className="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  id="email-id"
                  name="email"
                  autoComplete="true"
                />
              </div>
            </div>
            <div className="input">
              <label className="label" htmlFor="Password">
                Password
              </label>
              <div className="log-pass">
                <input
                  type={showPassword ? "text" : "password"}
                  className="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  id="password-id"
                  name="password"
                  autoComplete="true"
                />
                <span
                  className="toggle-password"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  <FontAwesomeIcon
                    className="icon"
                    icon={showPassword ? faEyeSlash : faEye}
                  />{" "}
                </span>
              </div>
            </div>
            <div className="log-btn-main">
              <button className="log-btn" type="submit">
                Login
              </button>
              <Link className="reg-link-txt" href="/register">
                Don't have an account?Register Here
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
