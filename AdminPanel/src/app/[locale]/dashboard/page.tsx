"use client";

import Image from "next/image";
import { useState } from "react";
import {
  Settings,
  MessageSquare,
  FileSpreadsheet,
  
  Home,
 
  Bot,
  
  Activity,
  User
} from "lucide-react";
import { useTranslations } from 'next-intl';
import LocaleSwitcher from "@/app/components/LocaleSwitcher";
import SettingsPanel from "@/app/components/SettingsPanel";
import ModelsPanel from "@/app/components/ModelsPanel";
import ChatPanel from "@/app/components/ChatPanel";
import UsersPanel from "@/app/components/UsersPanel";
import { signOut } from "next-auth/react"
import ProfilePanel from "@/app/components/ProfilePanel";
import ReportsPanel from "@/app/components/ReportsPanel";
import LogPanel from "@/app/components/LogPanel";
import TemplatesPanel from "@/app/components/TemplatesPanel";
import DashboardPanel from "@/app/components/DashboardPanel";

export default function AdminPanel({ }) {
  // const t = useTranslations();
  const commonT = useTranslations('common');
  const navT = useTranslations('navigation');
  const dashT = useTranslations('dashboard');
  const userT = useTranslations('userMenu');
  const [activeTab, setActiveTab] = useState("dashboard");
  
  // Function to get the text name of the active tab
  const getActiveTabName = () => {
    switch (activeTab) {
      case "dashboard": return navT('dashboard');
      case "settings": return navT('settings');
      case "llm": return navT('llmConfig');
      case "chats": return navT('chatIntegration');
      case "users": return navT('users');
      case "profile": return userT('profile');
      case "reports": return navT('reports');
      case "logs": return navT('logs');
      case "templates": return navT('templates');
      default: return dashT('panel');
    }
  };

  return (
    <div className="drawer lg:drawer-open bg-base-200 min-h-screen">
      <input id="my-drawer-2" type="checkbox" className="drawer-toggle" />
      <div className="drawer-content flex flex-col p-4">
        {/* Top navbar */}
        <div className="navbar bg-base-100 rounded-box mb-4 shadow-md">
          <div className="flex-none lg:hidden">
            <label htmlFor="my-drawer-2" aria-label="open sidebar" className="btn btn-square btn-ghost">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="inline-block w-6 h-6 stroke-current"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
            </label>
          </div>
          <div className="flex-1">
            <h1 className="text-xl font-bold px-4 text-primary">{getActiveTabName()}</h1>
          </div>
          <div className="flex-none">
            <div className="dropdown dropdown-end">
              <div tabIndex={0} role="button" className="btn btn-ghost btn-circle avatar">
                <div className="w-10 rounded-full">
                  <img alt="Admin avatar" src="https://api.dicebear.com/7.x/avataaars/svg?seed=admin" />
                </div>
              </div>
              <ul tabIndex={0} className="text-base-content menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52">
                <li onClick={() => { setActiveTab('profile') }}><a>{userT('profile')}</a></li>
                <li onClick={() => { signOut() }}><a>{userT('logout')}</a></li>
              </ul>
            </div>
          </div>
        </div>

        {/* Main content area */}
        <div className="flex flex-col gap-6">
          {activeTab === "dashboard" && (
            <DashboardPanel />

          )}

          {activeTab === "settings" && (
            <div className="card bg-base-100 shadow-xl">
              <div className="card-body">
                <SettingsPanel />
              </div>
            </div>
          )}

          {activeTab === "llm" && (
            <div className="card bg-base-100 shadow-xl">
              <div className="card-body">
                <ModelsPanel />
              </div>
            </div>
          )}

          {activeTab === "chats" && (
            <div className="card bg-base-100 shadow-xl">
              <div className="card-body">
                <ChatPanel />
              </div>
            </div>
          )}

          {activeTab === "users" && (
            <div className="card bg-base-100 shadow-xl">
              <div className="card-body">
                <UsersPanel />
              </div>
            </div>
          )}

          {activeTab === "profile" && (
            <div className="card bg-base-100 shadow-xl">
              <div className="card-body">
                <ProfilePanel />
              </div>
            </div>
          )}

          {activeTab === "reports" && (
            <div className="card bg-base-100 shadow-xl">
              <div className="card-body">
                <ReportsPanel />
              </div>
            </div>
          )}

          {activeTab === "logs" && (
            <div className="card bg-base-100 shadow-xl">
              <div className="card-body">
                <LogPanel />
              </div>
            </div>
          )}

          {activeTab === "templates" && (
            <div className="card bg-base-100 shadow-xl">
              <div className="card-body">
                <TemplatesPanel />
              </div>
            </div>
          )}

        </div>
      </div>

      {/* Sidebar */}
      <div className="drawer-side z-10">
        <label htmlFor="my-drawer-2" aria-label="close sidebar" className="drawer-overlay"></label>
        <div className="menu p-4 w-80 min-h-full bg-base-100 text-base-content gap-2">
          <div className="flex items-center gap-3 px-4 py-2">
            <div className="avatar">
              <div className="w-12 rounded-full bg-primary/10 p-1">
                <Image src="/next.svg" alt="Logo" width={48} height={48} className="dark:invert" />
              </div>
            </div>
            <div>
              <h2 className="font-bold text-xl">{commonT('appName')}</h2>
              <p className="text-xs opacity-60">{commonT('subtitle')}</p>
            </div>
          </div>
          <div className="divider"></div>
          <ul className="space-y-2">
            <li>
              <button
                className={`flex items-center p-2 ${activeTab === "dashboard" ? "bg-primary text-primary-content" : "hover:bg-base-200"} rounded-lg`}
                onClick={() => setActiveTab("dashboard")}>
                <Home size={20} />
                <span className="ml-3">{navT('dashboard')}</span>
              </button>
            </li>
            <li>
              <button
                className={`flex items-center p-2 ${activeTab === "chats" ? "bg-primary text-primary-content" : "hover:bg-base-200"} rounded-lg`}
                onClick={() => setActiveTab("chats")}>
                <MessageSquare size={20} />
                <span className="ml-3">{navT('chatIntegration')}</span>
              </button>
            </li>
            <li>
              <button
                className={`flex items-center p-2 ${activeTab === "reports" ? "bg-primary text-primary-content" : "hover:bg-base-200"} rounded-lg`}
                onClick={() => setActiveTab("reports")}>
                <FileSpreadsheet size={20} />
                <span className="ml-3">{navT('reports')}</span>
              </button>
            </li>
            <li>
              <button
                className={`flex items-center p-2 ${activeTab === "templates" ? "bg-primary text-primary-content" : "hover:bg-base-200"} rounded-lg`}
                onClick={() => setActiveTab("templates")}>
                <FileSpreadsheet size={20} />
                <span className="ml-3">{navT('templates')}</span>
              </button>
            </li>
            <li>
              <button
                className={`flex items-center p-2 ${activeTab === "llm" ? "bg-primary text-primary-content" : "hover:bg-base-200"} rounded-lg`}
                onClick={() => setActiveTab("llm")}>
                <Bot size={20} />
                <span className="ml-3">{navT('llmConfig')}</span>
                <span className="badge badge-sm badge-secondary ml-auto">{navT('api')}</span>
              </button>
            </li>

            <li>
              <button
                className={`flex items-center p-2 ${activeTab === "users" ? "bg-primary text-primary-content" : "hover:bg-base-200"} rounded-lg`}
                onClick={() => setActiveTab("users")}>
                <User size={20} />
                <span className="ml-3">{navT('users')}</span>
              </button>
            </li>

            <li>
              <button
                className={`flex items-center p-2 ${activeTab === "logs" ? "bg-primary text-primary-content" : "hover:bg-base-200"} rounded-lg`}
                onClick={() => setActiveTab("logs")}>
                <Activity size={20} />
                <span className="ml-3">{navT('logs')}</span>
              </button>
            </li>

            <li>
              <button
                className={`flex items-center p-2 ${activeTab === "settings" ? "bg-primary text-primary-content" : "hover:bg-base-200"} rounded-lg`}
                onClick={() => setActiveTab("settings")}>
                <Settings size={20} />
                <span className="ml-3">{navT('settings')}</span>
              </button>
            </li>
          </ul>
          <div className="divider"></div>
          <LocaleSwitcher />

        </div>
      </div>
    </div>
  );
}