"use client";

import { Float, OrbitControls } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";

type ReadinessStatus = "needs_immediate_support" | "watch" | "ready_to_progress";

type StudentSceneProps = {
  readinessStatus: ReadinessStatus;
  readinessScore: number;
  cohortGap: number | null;
};

function toneForStatus(status: ReadinessStatus) {
  if (status === "needs_immediate_support") {
    return {
      body: "#d9613d",
      accent: "#ffb38a",
      glow: "#ff8d66",
      floor: "#3f1f1f",
    };
  }
  if (status === "ready_to_progress") {
    return {
      body: "#1b7f8a",
      accent: "#8ce3d5",
      glow: "#52d0c5",
      floor: "#152d36",
    };
  }
  return {
    body: "#e1b04b",
    accent: "#ffe09a",
    glow: "#ffd36e",
    floor: "#3d3520",
  };
}

function AvatarFigure({
  color,
  accent,
  position,
  scale,
  muted = false,
  phase = 0,
}: {
  color: string;
  accent: string;
  position: [number, number, number];
  scale: number;
  muted?: boolean;
  phase?: number;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const materialProps = muted
    ? { metalness: 0.05, roughness: 0.92, opacity: 0.36, transparent: true }
    : { metalness: 0.22, roughness: 0.44 };

  useFrame((state) => {
    if (!groupRef.current) {
      return;
    }
    const t = state.clock.getElapsedTime() + phase;
    groupRef.current.position.y = position[1] + Math.sin(t * 1.2) * 0.08;
    groupRef.current.rotation.y = Math.sin(t * 0.5) * 0.14;
  });

  return (
    <group ref={groupRef} position={position} scale={scale}>
      <mesh position={[0, 2.9, 0]} castShadow>
        <sphereGeometry args={[0.48, 32, 32]} />
        <meshStandardMaterial color={accent} {...materialProps} />
      </mesh>

      <mesh position={[0, 1.65, 0]} castShadow>
        <capsuleGeometry args={[0.5, 1.5, 8, 16]} />
        <meshStandardMaterial color={color} {...materialProps} />
      </mesh>

      <mesh position={[-0.78, 1.82, 0]} rotation={[0, 0, 0.42]} castShadow>
        <capsuleGeometry args={[0.12, 0.9, 6, 12]} />
        <meshStandardMaterial color={accent} {...materialProps} />
      </mesh>
      <mesh position={[0.78, 1.82, 0]} rotation={[0, 0, -0.42]} castShadow>
        <capsuleGeometry args={[0.12, 0.9, 6, 12]} />
        <meshStandardMaterial color={accent} {...materialProps} />
      </mesh>

      <mesh position={[-0.28, 0.42, 0.04]} rotation={[0, 0, 0.08]} castShadow>
        <capsuleGeometry args={[0.14, 1.18, 6, 12]} />
        <meshStandardMaterial color={color} {...materialProps} />
      </mesh>
      <mesh position={[0.28, 0.42, 0.04]} rotation={[0, 0, -0.08]} castShadow>
        <capsuleGeometry args={[0.14, 1.18, 6, 12]} />
        <meshStandardMaterial color={color} {...materialProps} />
      </mesh>
    </group>
  );
}

function SignalRings({
  color,
  readinessScore,
}: {
  color: string;
  readinessScore: number;
}) {
  const innerRef = useRef<THREE.Mesh>(null);
  const outerRef = useRef<THREE.Mesh>(null);
  const lift = 0.1 + (1 - readinessScore) * 0.35;

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (innerRef.current) {
      innerRef.current.rotation.x = Math.PI / 2;
      innerRef.current.rotation.z = t * 0.55;
      innerRef.current.position.y = 0.28 + Math.sin(t * 1.4) * 0.03;
    }
    if (outerRef.current) {
      outerRef.current.rotation.x = Math.PI / 2;
      outerRef.current.rotation.z = -t * 0.35;
      outerRef.current.position.y = 0.48 + Math.cos(t * 1.1) * 0.04;
    }
  });

  return (
    <>
      <mesh ref={innerRef} position={[0, 0.28, 0]}>
        <torusGeometry args={[1.18, 0.04, 16, 120]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.18 + lift} />
      </mesh>
      <mesh ref={outerRef} position={[0, 0.48, 0]}>
        <torusGeometry args={[1.76, 0.03, 16, 120]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.08 + lift * 0.45} transparent opacity={0.9} />
      </mesh>
    </>
  );
}

function CohortMarkers({ cohortGap }: { cohortGap: number | null }) {
  const markerOffset = cohortGap == null ? 0 : Math.max(-0.55, Math.min(0.55, cohortGap * 2.2));

  return (
    <>
      <mesh position={[-3.2, 0.08 + markerOffset * 0.18, -0.2]} castShadow>
        <cylinderGeometry args={[0.28, 0.28, 0.18, 32]} />
        <meshStandardMaterial color="#f2efe8" metalness={0.05} roughness={0.92} />
      </mesh>
      <mesh position={[3.2, 0.08 - markerOffset * 0.18, -0.2]} castShadow>
        <cylinderGeometry args={[0.28, 0.28, 0.18, 32]} />
        <meshStandardMaterial color="#f2efe8" metalness={0.05} roughness={0.92} />
      </mesh>
    </>
  );
}

function Stage({
  readinessStatus,
  readinessScore,
  cohortGap,
}: StudentSceneProps) {
  const tone = toneForStatus(readinessStatus);

  return (
    <>
      <color attach="background" args={["#09101a"]} />
      <fog attach="fog" args={["#09101a", 10, 18]} />
      <ambientLight intensity={0.9} />
      <spotLight
        position={[3.5, 8, 4.2]}
        angle={0.4}
        penumbra={1}
        intensity={70}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
      />
      <pointLight position={[-4, 4, 3]} intensity={24} color={tone.glow} />
      <pointLight position={[4, 2.5, -3]} intensity={16} color="#ffffff" />

      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow position={[0, -0.01, 0]}>
        <circleGeometry args={[7.8, 64]} />
        <meshStandardMaterial color={tone.floor} metalness={0.14} roughness={0.88} />
      </mesh>

      <mesh position={[0, 0.16, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[2.35, 2.8, 0.3, 48]} />
        <meshStandardMaterial color="#18263a" metalness={0.16} roughness={0.62} />
      </mesh>

      <CohortMarkers cohortGap={cohortGap} />

      <Float speed={1.1} rotationIntensity={0.18} floatIntensity={0.2}>
        <AvatarFigure color={tone.body} accent={tone.accent} position={[0, 0.18, 0]} scale={1} />
      </Float>
      <AvatarFigure
        color="#6e7889"
        accent="#b4c0cb"
        position={[-2.95, 0.02, -1.6]}
        scale={0.74}
        muted
        phase={0.8}
      />
      <AvatarFigure
        color="#6e7889"
        accent="#b4c0cb"
        position={[2.95, 0.02, -1.6]}
        scale={0.74}
        muted
        phase={2.1}
      />

      <SignalRings color={tone.glow} readinessScore={readinessScore} />

      <OrbitControls
        enablePan={false}
        enableZoom={false}
        minPolarAngle={Math.PI / 2.7}
        maxPolarAngle={Math.PI / 2.15}
        autoRotate
        autoRotateSpeed={0.35}
      />
    </>
  );
}

export function StudentScene(props: StudentSceneProps) {
  return (
    <Canvas
      dpr={[1, 1.5]}
      shadows
      camera={{ position: [0, 3.1, 8.8], fov: 34 }}
      className="h-full w-full"
    >
      <Stage {...props} />
    </Canvas>
  );
}
