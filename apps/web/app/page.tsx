"use client";

import dynamic from "next/dynamic";

const GameApp = dynamic(() => import("@/features/game/components/GameApp").then((module) => module.GameApp), { ssr: false });

const Home = () => <GameApp />;

export default Home;
