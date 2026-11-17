import { useMemo } from "react";

const LITE_QUERY = "lite";
const PHONE_MAX_WIDTH = 820;

/** Phones and touch tablets get the lighter island model; `?lite=1` or `?lite=0` overrides. */
export const useIsLiteQuality = (): boolean =>
  useMemo(() => {
    const forced = new URLSearchParams(window.location.search).get(LITE_QUERY);

    if (forced !== null) {
      return forced === "1";
    }

    return window.matchMedia("(pointer: coarse)").matches || window.innerWidth < PHONE_MAX_WIDTH;
  }, []);
