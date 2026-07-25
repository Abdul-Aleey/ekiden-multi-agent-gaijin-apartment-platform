/** Faint background map of Japan's prefectures — real geographic data.
 * Source: "Japan prefectures.svg" by Andreasl01, Wikimedia Commons,
 * CC0 1.0 Universal (public domain). https://commons.wikimedia.org/wiki/File:Japan_prefectures.svg
 * Served from /public/japan-map.svg, desaturated and dimmed via CSS — decorative only. */
export default function JapanNetworkMap() {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/japan-map.svg"
      alt=""
      aria-hidden="true"
      className="w-full h-full object-contain grayscale opacity-[0.10] dark:opacity-[0.16]"
    />
  );
}
