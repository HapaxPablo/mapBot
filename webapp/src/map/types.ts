export interface Point {
  id: string;
  title: string;
  point_type: string;
  point_type_icon: string;
  description: string | null;
  lat: number;
  lng: number;
  photo_url: string | null;
  likes: number;
  dislikes: number;
}

export interface PointsMessage {
  type: "points" | "error";
  scope?: "all" | "personal";
  points?: Point[];
}

export interface PointBounds {
  west: number;
  south: number;
  east: number;
  north: number;
}
